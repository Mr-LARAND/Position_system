#include <Arduino.h>

const int dir_pin = 10;
const int step_pin = 9;
const int enable_pin = 8;
const int ms1_pin = 7; // пин для управления микрошагами MS1
const float step_size = 0.9; // 0.9° на шаг (400 шагов/оборот)
const int micro_Delay = 1000; // Задержка между шагами
float Starting_angle = 0.0; // Текущая позиция в градусах

void setup() 
{
  // Настройка пинов
  pinMode(dir_pin, OUTPUT);
  pinMode(step_pin, OUTPUT);
  pinMode(enable_pin, OUTPUT);
  pinMode(ms1_pin, OUTPUT);
  
  // Активация полушагового режима (MS1=HIGH(5V), MS2 и MS3 не подключены)
  digitalWrite(ms1_pin, HIGH); // Включаем полушаг
  digitalWrite(enable_pin, LOW); // Включаем драйвер
  
  Serial.begin(9600);
  Serial.println("Введите угол (0-359) или +/- угол (например +45):");
}


// Ф-я нормализации угла
float normalize_angle(float angle) 
{
  while(angle >= 360) 
    angle -= 360;
  while(angle < 0) 
    angle += 360;
  return angle;
}

void move_To_Angle(float Entered_angle) 
{
  Entered_angle = normalize_angle(Entered_angle);

  float difference = Entered_angle - Starting_angle;
  if(difference > 180) 
    difference -= 360;
  else if(difference < -180) 
    difference += 360;

  // Рассчитываем количество шагов, учитывая 400 шагов это оборот
  int steps = round(abs(difference) / step_size);
  digitalWrite(dir_pin, difference > 0 ? HIGH : LOW);

  // Выполняем шаги с оптимизированной задержкой
  for(int i = 0; i < steps; i++) {
    digitalWrite(step_pin, HIGH);
    delayMicroseconds(micro_Delay);
    digitalWrite(step_pin, LOW);
    delayMicroseconds(micro_Delay);
  }

  Starting_angle = Entered_angle;
}

void loop() 
{
  if(Serial.available() > 0) 
  {
    String input = Serial.readStringUntil('\n');
    input.trim();
    
    if(input.startsWith("+")) {
      float delta = input.substring(1).toFloat();
      float new_angle = normalize_angle(Starting_angle + delta);
      move_To_Angle(new_angle);
      Serial.print("Новый угол: ");
      Serial.println(new_angle, 1);
    }
    else if(input.startsWith("-")) {
      float delta = input.substring(1).toFloat();
      float new_angle = normalize_angle(Starting_angle - delta);
      move_To_Angle(new_angle);
      Serial.print("Новый угол: ");
      Serial.println(new_angle, 1);
    }
    else 
    {
      float angle = input.toFloat();
      normalize_angle(angle);
      move_To_Angle(angle);
      Serial.print("Угол установлен: ");
      Serial.println(angle, 1);
    }
  }
}