#include <Arduino.h>
#include <math.h>
#include "HX711.h"

namespace {
constexpr uint8_t kChannelCount = 7;
constexpr unsigned long kSerialBaudRate = 115200UL;
constexpr unsigned long kSampleRateHz = 80UL;
constexpr unsigned long kSamplePeriodMicros = 1000000UL / kSampleRateHz;
constexpr unsigned long kReadyTimeoutMs = 10UL;
constexpr unsigned long kReadyPollDelayMs = 1UL;
constexpr uint8_t kSensorActivationReads = 10;
constexpr uint8_t kCalibrationWarmupReads = 5;
constexpr uint8_t kCalibrationBatchCount = 3;
constexpr uint8_t kCalibrationBatchSampleCount = 17;
constexpr unsigned long kCalibrationReadDelayMicros = 1000UL;
constexpr unsigned long kCalibrationBatchSettleDelayMs = 20UL;
constexpr double kMaxChangeThreshold = 100000.0;
constexpr double kCalibrationBatchSpreadThreshold = 2000.0;

constexpr uint8_t kLoadcellDoutPins[kChannelCount] = {4, 6, 8, 10, 19, 3, 14};
constexpr uint8_t kLoadcellSckPins[kChannelCount] = {5, 7, 9, 18, 20, 2, 15};

HX711 g_scales[kChannelCount];
double g_offsets[kChannelCount] = {0, 0, 0, 0, 0, 0, 0};
double g_previous_values[kChannelCount] = {0, 0, 0, 0, 0, 0, 0};
double g_current_values[kChannelCount] = {0, 0, 0, 0, 0, 0, 0};

void emitStatus(const char* message) {
  Serial.print(F("status,"));
  Serial.println(message);
}

void emitStatusChannelValue(const char* message, uint8_t channel, long value) {
  Serial.print(F("status,"));
  Serial.print(message);
  Serial.print(',');
  Serial.print(channel);
  Serial.print(',');
  Serial.println(value);
}

void emitWarnChannel(const char* reason, uint8_t channel) {
  Serial.print(F("warn,"));
  Serial.print(reason);
  Serial.print(',');
  Serial.println(channel);
}

void emitWarnChannelValue(const char* reason, uint8_t channel, double value) {
  Serial.print(F("warn,"));
  Serial.print(reason);
  Serial.print(',');
  Serial.print(channel);
  Serial.print(',');
  Serial.println(value);
}

void printVectorLine(unsigned long timestamp_ms, const double* values) {
  Serial.print(F("vector,"));
  Serial.print(timestamp_ms);
  for (uint8_t i = 0; i < kChannelCount; ++i) {
    Serial.print(',');
    Serial.print(values[i]);
  }
  Serial.println();
}

bool waitForReady(uint8_t channel) {
  return g_scales[channel].wait_ready_timeout(kReadyTimeoutMs, kReadyPollDelayMs);
}

long readSignedReading(uint8_t channel) {
  return -g_scales[channel].read();
}

bool collectReadings(uint8_t channel, uint8_t sampleCount, long* samples, const char* timeoutReason) {
  if (sampleCount == 0) {
    return false;
  }

  for (uint8_t i = 0; i < sampleCount; ++i) {
    if (!waitForReady(channel)) {
      emitWarnChannel(timeoutReason, channel);
      return false;
    }

    samples[i] = readSignedReading(channel);
    delayMicroseconds(kCalibrationReadDelayMicros);
  }

  return true;
}

double trimmedMean(const long* samples, uint8_t sampleCount) {
  if (sampleCount == 0) {
    return 0.0;
  }

  long sum = 0;
  long min_value = samples[0];
  long max_value = samples[0];
  for (uint8_t i = 0; i < sampleCount; ++i) {
    const long value = samples[i];
    sum += value;
    if (value < min_value) {
      min_value = value;
    }
    if (value > max_value) {
      max_value = value;
    }
  }

  if (sampleCount <= 2) {
    return static_cast<double>(sum) / static_cast<double>(sampleCount);
  }

  const long trimmed_sum = sum - min_value - max_value;
  return static_cast<double>(trimmed_sum) / static_cast<double>(sampleCount - 2);
}

double medianOfThree(double a, double b, double c) {
  if (a > b) {
    const double t = a;
    a = b;
    b = t;
  }
  if (b > c) {
    const double t = b;
    b = c;
    c = t;
  }
  if (a > b) {
    const double t = a;
    a = b;
    b = t;
  }
  return b;
}

double maxMinusMin(const double* values, uint8_t count) {
  if (count == 0) {
    return 0.0;
  }

  double min_value = values[0];
  double max_value = values[0];
  for (uint8_t i = 1; i < count; ++i) {
    if (values[i] < min_value) {
      min_value = values[i];
    }
    if (values[i] > max_value) {
      max_value = values[i];
    }
  }

  return max_value - min_value;
}

void warmupChannel(uint8_t channel) {
  for (uint8_t i = 0; i < kSensorActivationReads; ++i) {
    if (!waitForReady(channel)) {
      emitWarnChannel("warmup_timeout", channel);
      return;
    }
    (void)g_scales[channel].read();
    delay(10);
  }
}

bool calibrateChannel(uint8_t channel) {
  emitStatusChannelValue("calibration_channel_start", channel, 0);

  for (uint8_t i = 0; i < kCalibrationWarmupReads; ++i) {
    if (!waitForReady(channel)) {
      emitWarnChannel("calibration_warmup_timeout", channel);
      break;
    }
    (void)g_scales[channel].read();
    delay(10);
  }

  double batch_means[kCalibrationBatchCount] = {0.0, 0.0, 0.0};
  long samples[kCalibrationBatchSampleCount];

  for (uint8_t batch = 0; batch < kCalibrationBatchCount; ++batch) {
    if (!collectReadings(channel, kCalibrationBatchSampleCount, samples, "calibration_timeout")) {
      emitWarnChannel("calibration_skipped", channel);
      return false;
    }

    batch_means[batch] = trimmedMean(samples, kCalibrationBatchSampleCount);
    if (batch + 1 < kCalibrationBatchCount) {
      delay(kCalibrationBatchSettleDelayMs);
    }
  }

  const double batch_spread = maxMinusMin(batch_means, kCalibrationBatchCount);
  if (batch_spread > kCalibrationBatchSpreadThreshold) {
    emitWarnChannelValue("calibration_spread", channel, batch_spread);
  }

  g_offsets[channel] = medianOfThree(batch_means[0], batch_means[1], batch_means[2]);

  g_previous_values[channel] = 0.0;

  emitStatusChannelValue("calibration_channel_end", channel, lround(g_offsets[channel]));
  return true;
}

void initializeScales() {
  emitStatus("sensor_init_start");

  for (uint8_t channel = 0; channel < kChannelCount; ++channel) {
    g_scales[channel].begin(kLoadcellDoutPins[channel], kLoadcellSckPins[channel]);
    warmupChannel(channel);
  }

  emitStatus("sensor_init_end");
}

void calibrateAllChannels() {
  emitStatus("calibration_start");

  for (uint8_t channel = 0; channel < kChannelCount; ++channel) {
    (void)calibrateChannel(channel);
  }

  emitStatus("calibration_end");
}

void handleSerialCommands() {
  while (Serial.available() > 0) {
    const char command = static_cast<char>(Serial.read());
    switch (command) {
      case 'c':
        emitStatus("calibration_command_received");
        calibrateAllChannels();
        break;
      default:
        break;
    }
  }
}

bool readChannelValue(uint8_t channel, double* value) {
  if (!waitForReady(channel)) {
    emitWarnChannel("ready_timeout", channel);
    *value = g_previous_values[channel];
    return false;
  }

  const double reading = readSignedReading(channel);
  const double adjusted = reading - g_offsets[channel];

  if (fabs(adjusted - g_previous_values[channel]) > kMaxChangeThreshold) {
    *value = g_previous_values[channel];
    emitWarnChannelValue("spike", channel, *value);
  } else {
    *value = adjusted;
  }

  g_previous_values[channel] = *value;
  return true;
}

void updateAllValues() {
  for (uint8_t channel = 0; channel < kChannelCount; ++channel) {
    (void)readChannelValue(channel, &g_current_values[channel]);
  }
}
}  // namespace

void setup() {
  Serial.begin(kSerialBaudRate);
  emitStatus("setup_start");

  initializeScales();
  calibrateAllChannels();

  emitStatus("setup_end");
}

void loop() {
  const unsigned long cycle_start_us = micros();

  handleSerialCommands();
  updateAllValues();
  printVectorLine(millis(), g_current_values);

  while (micros() - cycle_start_us < kSamplePeriodMicros) {
  }
}
