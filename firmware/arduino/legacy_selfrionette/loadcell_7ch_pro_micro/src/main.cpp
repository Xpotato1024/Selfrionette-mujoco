#include <Arduino.h>
#include <math.h>
#include "HX711.h"

namespace {
constexpr uint8_t kChannelCount = 7;
constexpr unsigned long kSerialBaudRate = 115200UL;
constexpr unsigned long kSampleRateHz = 200UL;
constexpr unsigned long kSamplePeriodMicros = 1000000UL / kSampleRateHz;
constexpr unsigned long kReadyTimeoutMs = 10UL;
constexpr unsigned long kReadyPollDelayMs = 1UL;
constexpr uint8_t kSensorActivationReads = 10;
constexpr uint8_t kCalibrationWarmupReads = 5;
constexpr uint16_t kCalibrationSampleCount = 50;
constexpr unsigned long kCalibrationReadDelayMicros = 1000UL;
constexpr double kMaxChangeThreshold = 100000.0;

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

  long sum = 0;
  uint16_t collected = 0;

  for (; collected < kCalibrationSampleCount; ++collected) {
    if (!waitForReady(channel)) {
      emitWarnChannel("calibration_timeout", channel);
      break;
    }

    sum += g_scales[channel].read();
    delayMicroseconds(kCalibrationReadDelayMicros);
  }

  if (collected == 0) {
    emitWarnChannel("calibration_skipped", channel);
    return false;
  }

  const long mean = sum / collected;
  g_offsets[channel] = -static_cast<double>(mean);
  g_previous_values[channel] = 0.0;

  emitStatusChannelValue("calibration_channel_end", channel, mean);
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

bool readChannelValue(uint8_t channel, double* value) {
  if (!waitForReady(channel)) {
    emitWarnChannel("ready_timeout", channel);
    *value = g_previous_values[channel];
    return false;
  }

  const long reading = -g_scales[channel].read();
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

  updateAllValues();
  printVectorLine(millis(), g_current_values);

  while (micros() - cycle_start_us < kSamplePeriodMicros) {
  }
}
