/* 
Данный скетч НЕ ЗАЛИТ в Arduino nano
Простое по, пользователь вводит угол, мотор на него становится
*/

#include <Arduino.h>

const int dir_pin = 10;
const int step_pin = 9;
const int enable_pin = 8;
const int ms1_pin = 7;  // пин для управления микрошагами MS1
const float step_size = 0.9; // 400 шагов 360° -> 0,9° на шаг
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
  Serial.println("Positioning system");
  Serial.println("Enter angle (0-359):");
}


// Ф-я которая поворачивает угол (ф-я умная, т.е. поворачивает угол по кратчайшему пути)
void move_To_Angle(float Entered_angle) 
{
  // Вычисляем разницу с учетом кратчайшего пути
  float difference = Entered_angle - Starting_angle;
  if (difference > 180) 
    difference -= 360;
  else if (difference < -180) 
    difference += 360;

  // Рассчитываем количество шагов, учитывая 400 шагов это оборот
  int steps = round(abs(difference) / step_size);
  digitalWrite(dir_pin, difference > 0 ? HIGH : LOW); // Подаем 5V, если разница изменилась, инчае 0V

  // Выполняем шаги с оптимизированной задержкой
  for (int i = 0; i < steps; i++) {
    digitalWrite(step_pin, HIGH);
    delayMicroseconds(micro_Delay);
    digitalWrite(step_pin, LOW);
    delayMicroseconds(micro_Delay);
  }

  Starting_angle = Entered_angle;
}


// Главная функция
void loop() 
{
  if (Serial.available() > 0) // Проверяем, что буфер не пустой
  {
    float Entered_angle = Serial.parseFloat(); // парсим ввёденный угол
    
    if (Entered_angle >= 0 && Entered_angle < 360) 
    {
      move_To_Angle(Entered_angle);
      Serial.print("Installed: ");
      Serial.print(Entered_angle, 1);
      Serial.println("°");
    } 
    else 
    {
      Serial.println("Error! Enter 0-359.9");
    }

    // Очищаем буфер от оставшихся символов (включая \r и \n)
    while(Serial.available() > 0) 
      Serial.read();
  }
}