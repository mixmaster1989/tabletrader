import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import warnings
warnings.filterwarnings('ignore')

class TradingPatternAnalyzer:
    """
    Анализатор торговых паттернов для выявления алгоритмов трейдера
    """
    
    def __init__(self, logger=None):
        self.logger = logger
        self.patterns = {}
        self.features = []
        self.model = None
        
    def log(self, message, level="INFO"):
        """Логирование с поддержкой внешнего логгера"""
        if self.logger:
            if level == "INFO":
                self.logger.info(message)
            elif level == "WARNING":
                self.logger.warning(message)
            elif level == "ERROR":
                self.logger.error(message)
        else:
            print(f"[{level}] {message}")
    
    def prepare_data(self, signals):
        """
        Подготовка данных для анализа
        """
        self.log("🔍 Подготовка данных для анализа паттернов...")
        
        # Создаем DataFrame из сигналов
        df = pd.DataFrame(signals)
        
        # Конвертируем даты
        df['entry_date'] = pd.to_datetime(df['entry_date'], format='%d.%m.%Y %H:%M')
        
        # Для закрытых сделок используем entry_date как exit_date (так как exit_date нет в данных)
        # Это упрощение, но позволяет анализировать паттерны
        df['exit_date'] = df['entry_date']
        
        # Добавляем временные характеристики
        df['hour'] = df['entry_date'].dt.hour
        df['day_of_week'] = df['entry_date'].dt.dayofweek
        df['month'] = df['entry_date'].dt.month
        
        # Добавляем технические характеристики
        df['price_range'] = abs(df['entry_price'] - df['exit_price'])
        df['price_range_pct'] = (df['price_range'] / df['entry_price']) * 100
        df['stop_loss_distance'] = abs(df['entry_price'] - df['stop_loss'])
        df['stop_loss_distance_pct'] = (df['stop_loss_distance'] / df['entry_price']) * 100
        
        # Добавляем риск-менеджмент характеристики
        df['risk_reward_ratio'] = df['price_range_pct'] / df['stop_loss_distance_pct']
        
        # Добавляем направление как числовое значение
        df['direction_numeric'] = df['direction'].map({'LONG': 1, 'SHORT': -1})
        
        # Добавляем успешность сделки
        df['is_profitable'] = (df['profit_loss'] > 0).astype(int)
        
        self.log(f"✅ Подготовлено {len(df)} сделок для анализа")
        return df
    
    def analyze_time_patterns(self, df):
        """
        Анализ временных паттернов
        """
        self.log("⏰ Анализ временных паттернов...")
        
        patterns = {}
        
        # Анализ по часам
        hourly_stats = df.groupby('hour').agg({
            'is_profitable': ['count', 'mean'],
            'profit_loss': ['mean', 'std'],
            'direction_numeric': 'mean'
        }).round(3)
        
        patterns['hourly'] = {
            'most_profitable_hours': hourly_stats[hourly_stats[('is_profitable', 'mean')] > 0.6].index.tolist(),
            'least_profitable_hours': hourly_stats[hourly_stats[('is_profitable', 'mean')] < 0.4].index.tolist(),
            'stats': hourly_stats
        }
        
        # Анализ по дням недели
        daily_stats = df.groupby('day_of_week').agg({
            'is_profitable': ['count', 'mean'],
            'profit_loss': ['mean', 'std']
        }).round(3)
        
        patterns['daily'] = {
            'best_days': daily_stats[daily_stats[('is_profitable', 'mean')] > 0.6].index.tolist(),
            'worst_days': daily_stats[daily_stats[('is_profitable', 'mean')] < 0.4].index.tolist(),
            'stats': daily_stats
        }
        
        self.log(f"✅ Найдено {len(patterns['hourly']['most_profitable_hours'])} прибыльных часов")
        return patterns
    
    def analyze_price_patterns(self, df):
        """
        Анализ ценовых паттернов
        """
        self.log("💰 Анализ ценовых паттернов...")
        
        patterns = {}
        
        # Анализ по размеру позиции
        df['position_size_category'] = pd.cut(df['price_range_pct'], 
                                            bins=[0, 1, 2, 5, 10, 100], 
                                            labels=['Очень малая', 'Малая', 'Средняя', 'Большая', 'Очень большая'])
        
        size_stats = df.groupby('position_size_category').agg({
            'is_profitable': ['count', 'mean'],
            'profit_loss': ['mean', 'std']
        }).round(3)
        
        patterns['position_size'] = {
            'best_sizes': size_stats[size_stats[('is_profitable', 'mean')] > 0.6].index.tolist(),
            'stats': size_stats
        }
        
        # Анализ риск-менеджмента
        risk_stats = df.groupby(pd.cut(df['risk_reward_ratio'], bins=5)).agg({
            'is_profitable': ['count', 'mean'],
            'profit_loss': ['mean', 'std']
        }).round(3)
        
        patterns['risk_reward'] = {
            'optimal_ratios': risk_stats[risk_stats[('is_profitable', 'mean')] > 0.6].index.tolist(),
            'stats': risk_stats
        }
        
        self.log(f"✅ Проанализированы паттерны по размеру позиции и риск-менеджменту")
        return patterns
    
    def analyze_symbol_patterns(self, df):
        """
        Анализ паттернов по символам
        """
        self.log("📊 Анализ паттернов по символам...")
        
        patterns = {}
        
        symbol_stats = df.groupby('symbol').agg({
            'is_profitable': ['count', 'mean'],
            'profit_loss': ['mean', 'std'],
            'direction_numeric': 'mean',
            'price_range_pct': 'mean'
        }).round(3)
        
        patterns['symbols'] = {
            'most_profitable': symbol_stats[symbol_stats[('is_profitable', 'mean')] > 0.7].index.tolist(),
            'least_profitable': symbol_stats[symbol_stats[('is_profitable', 'mean')] < 0.3].index.tolist(),
            'long_bias': symbol_stats[symbol_stats[('direction_numeric', 'mean')] > 0.3].index.tolist(),
            'short_bias': symbol_stats[symbol_stats[('direction_numeric', 'mean')] < -0.3].index.tolist(),
            'stats': symbol_stats
        }
        
        self.log(f"✅ Найдено {len(patterns['symbols']['most_profitable'])} прибыльных символов")
        return patterns
    
    def cluster_analysis(self, df):
        """
        Кластерный анализ для выявления групп похожих сделок
        """
        self.log("🎯 Кластерный анализ сделок...")
        
        # Подготавливаем признаки для кластеризации
        features = ['hour', 'day_of_week', 'price_range_pct', 'stop_loss_distance_pct', 
                   'risk_reward_ratio', 'direction_numeric']
        
        X = df[features].fillna(0)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Определяем оптимальное количество кластеров
        inertias = []
        K_range = range(2, min(10, len(df) // 5))
        
        for k in K_range:
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            kmeans.fit(X_scaled)
            inertias.append(kmeans.inertia_)
        
        # Выбираем количество кластеров (упрощенный подход)
        optimal_k = 3 if len(K_range) >= 3 else 2
        
        # Выполняем кластеризацию
        kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
        df['cluster'] = kmeans.fit_predict(X_scaled)
        
        # Анализируем кластеры
        cluster_stats = df.groupby('cluster').agg({
            'is_profitable': ['count', 'mean'],
            'profit_loss': ['mean', 'std'],
            'symbol': 'nunique',
            'direction_numeric': 'mean',
            'hour': 'mean'
        }).round(3)
        
        patterns = {
            'clusters': {
                'optimal_k': optimal_k,
                'cluster_stats': cluster_stats,
                'cluster_centers': kmeans.cluster_centers_,
                'feature_names': features
            }
        }
        
        self.log(f"✅ Создано {optimal_k} кластеров сделок")
        return patterns
    
    def build_prediction_model(self, df):
        """
        Построение модели предсказания успешности сделок
        """
        self.log("🤖 Построение модели предсказания...")
        
        # Подготавливаем признаки
        features = ['hour', 'day_of_week', 'month', 'price_range_pct', 
                   'stop_loss_distance_pct', 'risk_reward_ratio', 'direction_numeric']
        
        X = df[features].fillna(0)
        y = df['is_profitable']
        
        # Разделяем данные
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Обучаем модель
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
        
        # Оцениваем модель
        train_score = model.score(X_train, y_train)
        test_score = model.score(X_test, y_test)
        
        # Важность признаков
        feature_importance = pd.DataFrame({
            'feature': features,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        patterns = {
            'prediction_model': {
                'model': model,
                'train_score': train_score,
                'test_score': test_score,
                'feature_importance': feature_importance,
                'features': features
            }
        }
        
        self.log(f"✅ Модель обучена (точность: {test_score:.3f})")
        return patterns
    
    def generate_trading_rules(self, patterns):
        """
        Генерация торговых правил на основе найденных паттернов
        """
        self.log("📋 Генерация торговых правил...")
        
        rules = []
        
        # Правила по времени
        if 'hourly' in patterns:
            profitable_hours = patterns['hourly']['most_profitable_hours']
            if profitable_hours:
                rules.append(f"🕐 Торговать в часы: {profitable_hours}")
            
            unprofitable_hours = patterns['hourly']['least_profitable_hours']
            if unprofitable_hours:
                rules.append(f"⏸️ Избегать часов: {unprofitable_hours}")
        
        if 'daily' in patterns:
            best_days = patterns['daily']['best_days']
            if best_days:
                day_names = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
                best_day_names = [day_names[day] for day in best_days]
                rules.append(f"📅 Лучшие дни: {best_day_names}")
        
        # Правила по символам
        if 'symbols' in patterns:
            profitable_symbols = patterns['symbols']['most_profitable']
            if profitable_symbols:
                rules.append(f"💎 Прибыльные символы: {profitable_symbols}")
            
            long_bias = patterns['symbols']['long_bias']
            if long_bias:
                rules.append(f"📈 Склонность к LONG: {long_bias}")
            
            short_bias = patterns['symbols']['short_bias']
            if short_bias:
                rules.append(f"📉 Склонность к SHORT: {short_bias}")
        
        # Правила по размеру позиции
        if 'position_size' in patterns:
            best_sizes = patterns['position_size']['best_sizes']
            if best_sizes:
                rules.append(f"📏 Оптимальные размеры: {best_sizes}")
        
        # Правила по риск-менеджменту
        if 'risk_reward' in patterns:
            optimal_ratios = patterns['risk_reward']['optimal_ratios']
            if optimal_ratios:
                rules.append(f"⚖️ Оптимальные R/R: {optimal_ratios}")
        
        return rules
    
    def create_visualizations(self, df, patterns, save_path=None):
        """
        Создание визуализаций для анализа
        """
        self.log("📊 Создание визуализаций...")
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle('Анализ торговых паттернов', fontsize=16)
        
        # 1. Распределение прибыли
        axes[0, 0].hist(df['profit_loss'], bins=20, alpha=0.7, color='skyblue')
        axes[0, 0].set_title('Распределение прибыли/убытка')
        axes[0, 0].set_xlabel('P&L (%)')
        axes[0, 0].set_ylabel('Количество сделок')
        
        # 2. Прибыльность по часам
        if 'hourly' in patterns:
            hourly_data = patterns['hourly']['stats']
            axes[0, 1].bar(hourly_data.index, hourly_data[('is_profitable', 'mean')])
            axes[0, 1].set_title('Прибыльность по часам')
            axes[0, 1].set_xlabel('Час')
            axes[0, 1].set_ylabel('Доля прибыльных сделок')
        
        # 3. Прибыльность по символам
        if 'symbols' in patterns:
            symbol_data = patterns['symbols']['stats']
            top_symbols = symbol_data[('is_profitable', 'mean')].nlargest(10)
            axes[0, 2].barh(range(len(top_symbols)), top_symbols.values)
            axes[0, 2].set_yticks(range(len(top_symbols)))
            axes[0, 2].set_yticklabels(top_symbols.index)
            axes[0, 2].set_title('Топ-10 прибыльных символов')
            axes[0, 2].set_xlabel('Доля прибыльных сделок')
        
        # 4. Распределение по направлениям
        direction_counts = df['direction'].value_counts()
        axes[1, 0].pie(direction_counts.values, labels=direction_counts.index, autopct='%1.1f%%')
        axes[1, 0].set_title('Распределение по направлениям')
        
        # 5. Прибыльность по размерам позиции
        if 'position_size' in patterns:
            size_data = patterns['position_size']['stats']
            axes[1, 1].bar(range(len(size_data)), size_data[('is_profitable', 'mean')])
            axes[1, 1].set_title('Прибыльность по размеру позиции')
            axes[1, 1].set_xlabel('Размер позиции')
            axes[1, 1].set_ylabel('Доля прибыльных сделок')
            axes[1, 1].set_xticks(range(len(size_data)))
            axes[1, 1].set_xticklabels(size_data.index, rotation=45)
        
        # 6. Важность признаков для предсказания
        if 'prediction_model' in patterns:
            importance_data = patterns['prediction_model']['feature_importance']
            axes[1, 2].barh(range(len(importance_data)), importance_data['importance'])
            axes[1, 2].set_yticks(range(len(importance_data)))
            axes[1, 2].set_yticklabels(importance_data['feature'])
            axes[1, 2].set_title('Важность признаков')
            axes[1, 2].set_xlabel('Важность')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            self.log(f"✅ Графики сохранены в {save_path}")
        
        plt.show()
    
    def analyze_all(self, signals):
        """
        Полный анализ всех паттернов
        """
        self.log("🚀 Запуск полного анализа торговых паттернов...")
        
        # Подготавливаем данные
        df = self.prepare_data(signals)
        
        # Выполняем все виды анализа
        all_patterns = {}
        
        all_patterns.update(self.analyze_time_patterns(df))
        all_patterns.update(self.analyze_price_patterns(df))
        all_patterns.update(self.analyze_symbol_patterns(df))
        all_patterns.update(self.cluster_analysis(df))
        all_patterns.update(self.build_prediction_model(df))
        
        # Генерируем правила
        rules = self.generate_trading_rules(all_patterns)
        
        # Создаем отчет
        report = {
            'summary': {
                'total_trades': len(df),
                'profitable_trades': df['is_profitable'].sum(),
                'win_rate': df['is_profitable'].mean(),
                'avg_profit': df['profit_loss'].mean(),
                'total_profit': df['profit_loss'].sum()
            },
            'patterns': all_patterns,
            'rules': rules,
            'data': df
        }
        
        self.log("✅ Анализ завершен!")
        return report
    
    def print_report(self, report):
        """
        Вывод отчета в консоль
        """
        print("\n" + "="*60)
        print("📊 ОТЧЕТ АНАЛИЗА ТОРГОВЫХ ПАТТЕРНОВ")
        print("="*60)
        
        # Общая статистика
        summary = report['summary']
        print(f"\n📈 ОБЩАЯ СТАТИСТИКА:")
        print(f"   Всего сделок: {summary['total_trades']}")
        print(f"   Прибыльных: {summary['profitable_trades']}")
        print(f"   Винрейт: {summary['win_rate']:.1%}")
        print(f"   Средняя прибыль: {summary['avg_profit']:.2f}%")
        print(f"   Общая прибыль: {summary['total_profit']:.2f}%")
        
        # Торговые правила
        print(f"\n📋 ВЫЯВЛЕННЫЕ ПРАВИЛА:")
        for i, rule in enumerate(report['rules'], 1):
            print(f"   {i}. {rule}")
        
        # Топ-5 прибыльных символов
        if 'symbols' in report['patterns']:
            symbol_stats = report['patterns']['symbols']['stats']
            top_symbols = symbol_stats[('profit_loss', 'mean')].nlargest(5)
            print(f"\n💎 ТОП-5 ПРИБЫЛЬНЫХ СИМВОЛОВ:")
            for symbol, profit in top_symbols.items():
                win_rate = symbol_stats.loc[symbol, ('is_profitable', 'mean')]
                print(f"   {symbol}: {profit:.2f}% (винрейт: {win_rate:.1%})")
        
        # Лучшие часы
        if 'hourly' in report['patterns']:
            hourly_stats = report['patterns']['hourly']['stats']
            best_hours = hourly_stats[('is_profitable', 'mean')].nlargest(3)
            print(f"\n🕐 ЛУЧШИЕ ЧАСЫ ДЛЯ ТОРГОВЛИ:")
            for hour, win_rate in best_hours.items():
                print(f"   {hour}:00 - винрейт: {win_rate:.1%}")
        
        print("\n" + "="*60) 