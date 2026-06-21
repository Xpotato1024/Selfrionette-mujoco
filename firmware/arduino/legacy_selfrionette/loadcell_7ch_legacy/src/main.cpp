#include <Arduino.h>
#include "HX711.h"


int vaid_num_pin_2 = 2;
const int LOADCELL_DOUT_PINS[] = {4,6,8,10,19,3,14};
const int LOADCELL_SCK_PINS[] = {5,7,9,18,20,2,15};

// const int LOADCELL_DOUT_PINS[] = {8,14};
// const int LOADCELL_SCK_PINS[] = {9,15};
double offset[7] = {0,0,0,0,0,0,0};

// bool isLeader = true; //
bool isLeader = true; //

bool isRequested = false;
HX711 scales[7] = {HX711(),HX711(),HX711(),HX711(),HX711(),HX711(),HX711()};
double freq = 200; //Hz
double timer_start = 0;
int timer_init = 0;
double values_self[7] = {0,0,0,0,0,0,0};
double values_other[7] = {0,0,0,0,0,0,0};
double prev_values[7] = {0,0,0,0,0,0,0};
double timeout_ms = 10; //[ms]
double max_change_threshold = 100000.0; // センサ値の許容最大変化量（適切な値に調整してください）

void setup() {
  for (int i=0;i<10;i++) {
    Serial.println("checking");
    Serial.println(millis());
    delay(100);
  }
  Serial.begin(115200);
  // Serial1.begin(115200);
  Serial.println("setup start");
  for (int i=0;i<sizeof(LOADCELL_DOUT_PINS)/sizeof(LOADCELL_DOUT_PINS[0]);i++) {
    scales[i].begin(LOADCELL_DOUT_PINS[i],LOADCELL_SCK_PINS[i]);
    // センサーを活性化するために複数回読み取り
    for (int j = 0; j < 10; j++) {
      scales[i].read();
      delay(10);
    }
  }
  delay(1000);
  Serial.println("setup end");
  Serial.println("calib start...");

  for (int i=0;i<sizeof(LOADCELL_DOUT_PINS)/sizeof(LOADCELL_DOUT_PINS[0]);i++) {
    // センサーが安定するまで待機
    while (!scales[i].is_ready()) {
      delay(10);
    }

    // センサーを活性化させるために複数回読み取り
    for (int k = 0; k < 5; k++) {
      scales[i].read();
      delay(10);
    }

    // 50回の測定値を配列に保存
    long readings[50];
    long sum = 0;
    for (int j = 0; j < 50; j++) {
      readings[j] = scales[i].read();
      sum += readings[j];
      delayMicroseconds(1000);
    }

    // 平均値を計算
    long mean = sum / 50;
    offset[i] = -mean; // 手動キャリブレーションと同じ符号

    Serial.print(i);
    Serial.print(": mean=");
    Serial.print(mean);
    Serial.println(" finished.");
  }
  Serial.println("calib end...");
  timer_init = micros();

  // prev_valuesを実際のセンサー値で初期化
  for (int i=0;i<sizeof(LOADCELL_DOUT_PINS)/sizeof(LOADCELL_DOUT_PINS[0]);i++) {
    // キャリブレーション後は基準値が0になるので、prev_valuesも0に設定
    prev_values[i] = 0;
  }
}

void loop() {
  timer_start = micros();
  if (Serial.available()) {
    char cmd = Serial.read();
    switch (cmd)
    {
    case 'i':
      {
      /* code */
      Serial.println("offset setting...");
      if (isLeader) {
        Serial1.write("i\n");
      }
      for (int i=0;i<sizeof(LOADCELL_DOUT_PINS)/sizeof(LOADCELL_DOUT_PINS[0]);i++) {
        Serial.print("Calibrating sensor ");
        Serial.print(i);
        Serial.print(": ");

        // センサーを活性化
        while (!scales[i].is_ready()) {
          delay(10);
        }

        // センサーを安定させるために数回読み取り
        for (int k = 0; k < 5; k++) {
          scales[i].read();
          delay(10);
        }

        // 50回の測定値を配列に保存
        long readings[50];
        long sum = 0;
        for (int j = 0; j < 50; j++) {
          readings[j] = scales[i].read();
          sum += readings[j];
          delayMicroseconds(1000);
        }

        // 平均値を計算
        long mean = sum / 50;

        // 分散を計算
        long variance_sum = 0;
        for (int j = 0; j < 50; j++) {
          long diff = readings[j] - mean;
          variance_sum += diff * diff;
        }
        double variance = (double)variance_sum / 50.0;
        double std_dev = sqrt(variance);

        offset[i] = -mean;
        Serial.print("mean=");
        Serial.print(mean);
        Serial.print(", std_dev=");
        Serial.print(std_dev);
        Serial.print(", variance=");
        Serial.print(variance);

        // 安定性の評価
        if (std_dev < 100) {
          Serial.println(" - STABLE");
        } else if (std_dev < 500) {
          Serial.println(" - MODERATE");
        } else {
          Serial.println(" - UNSTABLE");
        }

        // キャリブレーション後にprev_valuesを更新
        prev_values[i] = 0; // キャリブレーション後は0が基準値
      }
      Serial.println("Calibration completed!");
      break;
      }
    default:
      break;
    }
  }

  if(!isLeader) {
    if (Serial1.available()) {
      char cmd = Serial1.read();
      switch (cmd)
      {
      case 'i':
        /* code */
        // Serial.println("offset setting...");
        for (int i=0;i<sizeof(LOADCELL_DOUT_PINS)/sizeof(LOADCELL_DOUT_PINS[0]);i++) {
          offset[i] = -scales[i].read_average(50);
          // キャリブレーション後にprev_valuesを更新
          prev_values[i] = 0; // キャリブレーション後は0が基準値
        }
        Serial1.print("calibration finished.");
        break;
      default:
        break;
      }
    }
  }

  // ロードセルの値の読み込み(Leader follower両方とも)
  for (int i=0;i<sizeof(LOADCELL_DOUT_PINS)/sizeof(LOADCELL_DOUT_PINS[0]);i++) {
    if (scales[i].is_ready()) {
      long reading = -scales[i].read();
      double new_value = reading - offset[i];

      // センサ値の変化が閾値を超えているかチェック
      if (abs(new_value - prev_values[i]) > max_change_threshold) {
        // 変化が大きすぎる場合は前フレームの値を使用
        values_self[i] = prev_values[i];
        // デバッグ用（必要に応じてコメントアウト）
        // Serial.print("Spike detected on sensor ");
        // Serial.println(i);
      } else {
        // 正常な変化の場合は新しい値を使用
        values_self[i] = new_value;
      }

      // 今回の値を保存（異常値の場合は前回の値がそのまま保存される）
      prev_values[i] = values_self[i];
    } else {
      values_self[i] = prev_values[i];
    }
  }
  String cmds = "";

  // リーダ、フォロワで役割の分岐
  if (isLeader) {
    // リーダーの挙動
    // フォロワーに信号を依頼
    double micros_command = micros();
    // 信号の読み出し, 応答を待つ。
    // while(!Serial1.available()) {
    //   Serial1.write("r\n");
    //   Serial.println("waiting...");
    //   delay(1);
    //   // if(micros_command - micros() < timeout_ms * 1000.0) break;
    // };
    // if (Serial1.available()) {
    //   cmds = Serial1.readStringUntil('\n');
    // } else {
    //   Serial.println("not comeback");
    //   return;
    // }

    Serial.print("vector,");
    Serial.print(millis());
    // Serial.print(",");
    // Serial.print(1000000.0/(micros() - timer_start));
    for (int i=0;i<sizeof(LOADCELL_DOUT_PINS)/sizeof(LOADCELL_DOUT_PINS[0]);i++) {
      Serial.print(",");
      Serial.print(values_self[i]);
    }
    // Serial.print(cmds);
    Serial.println();
    // リーダー時のみHzを調整する。フォロワーはその必要はない。
    while(micros() - timer_start < 1000000.0 / freq ) {};
  } else {

    // フォロワーの挙動
    // センサの値は常にStringにしておく。
    for (int i=0;i<vaid_num_pin_2;i++) {
      cmds += ',';
      cmds += String(values_self[i]);
    }
    cmds += "\n";
    // リーダーからの命令(文字列rのコマンド)を待つ
    while(!Serial1.available()) {
      Serial.println("waiting for leader command");
      delay(1);
    };
    if (Serial1.available()) {
      char cmd = Serial1.read();
      switch (cmd)
      {
      case 'r':
        /* code */
        isRequested = true;
        break;
      case 'i':
        /* code */
        // Serial.println("offset setting...");
        for (int i=0;i<sizeof(LOADCELL_DOUT_PINS)/sizeof(LOADCELL_DOUT_PINS[0]);i++) {
          offset[i] = -scales[i].read_average(50);
        }
        Serial1.print("calibration finished.");
        break;
      default:
        break;
      }
    }
    // リクエストされたときのみセンサ値を送るようにする。
    if (isRequested) {
      Serial1.print(cmds);
      isRequested = false;
    }
  }

}
