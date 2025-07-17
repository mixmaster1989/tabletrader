#!/usr/bin/env python3
"""
Тестовый скрипт для проверки анализатора торговых паттернов
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trading_analyzer import TradingPatternAnalyzer
import logging

def setup_logging():
    """Настройка логирования"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('pattern_analysis.log', encoding='utf-8')
        ]
    )
    return logging.getLogger(__name__)

def create_sample_data():
    """Создание тестовых данных для анализа"""
    sample_signals = [
        {
            'row': 1,
            'entry_date': '02.08.2024 12:15',
            'exit_date': '02.08.2024 13:45',
            'symbol': 'SOL',
            'entry_price': 163.4558,
            'direction': 'LONG',
            'exit_price': 164.6514,
            'stop_loss': 162.3237,
            'status': 'closed',
            'profit_loss': 0.7314515606053652
        },
        {
            'row': 2,
            'entry_date': '05.08.2024 14:00',
            'exit_date': '05.08.2024 14:15',
            'symbol': 'ADA',
            'entry_price': 0.29375,
            'direction': 'SHORT',
            'exit_price': 0.28916,
            'stop_loss': 0.29868,
            'status': 'closed',
            'profit_loss': 1.5625531914893749
        },
        {
            'row': 3,
            'entry_date': '05.08.2024 14:00',
            'exit_date': '05.08.2024 14:15',
            'symbol': 'NEAR',
            'entry_price': 3.2448,
            'direction': 'SHORT',
            'exit_price': 3.1803,
            'stop_loss': 3.3471,
            'status': 'closed',
            'profit_loss': 1.9877958579881723
        },
        {
            'row': 4,
            'entry_date': '05.08.2024 14:00',
            'exit_date': '05.08.2024 14:15',
            'symbol': 'PEOPLE',
            'entry_price': 0.04379,
            'direction': 'SHORT',
            'exit_price': 0.04334,
            'stop_loss': 0.04486,
            'status': 'closed',
            'profit_loss': 1.0276318794245396
        },
        {
            'row': 5,
            'entry_date': '05.08.2024 15:00',
            'exit_date': '05.08.2024 15:15',
            'symbol': 'ADA',
            'entry_price': 0.2971,
            'direction': 'LONG',
            'exit_price': 0.30115,
            'stop_loss': 0.28978,
            'status': 'closed',
            'profit_loss': 1.3631773813530792
        },
        {
            'row': 6,
            'entry_date': '05.08.2024 15:45',
            'exit_date': '05.08.2024 15:45',
            'symbol': 'ADA',
            'entry_price': 0.29139,
            'direction': 'SHORT',
            'exit_price': 0.28579,
            'stop_loss': 0.29871,
            'status': 'closed',
            'profit_loss': 1.9218229863756457
        },
        {
            'row': 7,
            'entry_date': '07.08.2024 11:15',
            'exit_date': '07.08.2024 13:30',
            'symbol': 'ADA',
            'entry_price': 0.33591,
            'direction': 'LONG',
            'exit_price': 0.34001,
            'stop_loss': 0.33181,
            'status': 'closed',
            'profit_loss': 1.2205650323003163
        },
        {
            'row': 8,
            'entry_date': '07.08.2024 11:45',
            'exit_date': '07.08.2024 14:30',
            'symbol': 'SOL',
            'entry_price': 153.6002,
            'direction': 'LONG',
            'exit_price': 156.1578,
            'stop_loss': 151.0426,
            'status': 'closed',
            'profit_loss': 1.6651019985651112
        },
        {
            'row': 9,
            'entry_date': '07.08.2024 14:00',
            'exit_date': '07.08.2024 14:00',
            'symbol': 'PEOPLE',
            'entry_price': 0.05608,
            'direction': 'SHORT',
            'exit_price': 0.05569,
            'stop_loss': 0.05726,
            'status': 'closed',
            'profit_loss': 0.6954350927246692
        },
        {
            'row': 10,
            'entry_date': '13.08.2024 14:15',
            'exit_date': '13.08.2024 15:30',
            'symbol': 'BNB',
            'entry_price': 521.484,
            'direction': 'LONG',
            'exit_price': 718.4,
            'stop_loss': 515.0,
            'status': 'closed',
            'profit_loss': 37.76
        },
        {
            'row': 11,
            'entry_date': '13.08.2024 15:00',
            'exit_date': '13.08.2024 15:30',
            'symbol': 'DOGE',
            'entry_price': 0.103672,
            'direction': 'SHORT',
            'exit_date': '13.08.2024 15:30',
            'exit_price': 0.21508,
            'stop_loss': 0.105,
            'status': 'closed',
            'profit_loss': -107.46
        },
        {
            'row': 12,
            'entry_date': '13.08.2024 16:00',
            'exit_date': '13.08.2024 16:30',
            'symbol': 'TON',
            'entry_price': 6.70662,
            'direction': 'LONG',
            'exit_price': 3.237,
            'stop_loss': 6.5,
            'status': 'closed',
            'profit_loss': -51.73
        }
    ]
    
    return sample_signals

def main():
    """Основная функция тестирования"""
    print("🧠 ТЕСТИРОВАНИЕ АНАЛИЗАТОРА ТОРГОВЫХ ПАТТЕРНОВ")
    print("=" * 60)
    
    # Настраиваем логирование
    logger = setup_logging()
    
    # Создаем анализатор
    analyzer = TradingPatternAnalyzer(logger)
    
    # Создаем тестовые данные
    sample_signals = create_sample_data()
    print(f"📊 Создано {len(sample_signals)} тестовых сделок")
    
    # Выполняем полный анализ
    print("\n🚀 Запуск анализа...")
    report = analyzer.analyze_all(sample_signals)
    
    # Выводим отчет
    print("\n" + "=" * 60)
    analyzer.print_report(report)
    
    # Создаем визуализации
    print("\n📊 Создание визуализаций...")
    try:
        analyzer.create_visualizations(report['data'], report['patterns'], 'pattern_analysis.png')
        print("✅ Графики сохранены в pattern_analysis.png")
    except Exception as e:
        print(f"⚠️ Ошибка создания графиков: {e}")
    
    print("\n✅ Тестирование завершено!")

if __name__ == "__main__":
    main() 