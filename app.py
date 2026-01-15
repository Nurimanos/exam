from flask import Flask, render_template, request, session, redirect, url_for
import json
import os

app = Flask(__name__)
app.secret_key = 'exam_app_secret_key_2026'  # Обязательно для сессий

# ====== ЗАГРУЗКА ВОПРОСОВ ИЗ JSON ======
def load_questions():
    """Загружает вопросы из файла questions.json"""
    try:
        # Находим путь к файлу questions.json
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, 'questions.json')
        
        # Читаем файл
        with open(json_path, 'r', encoding='utf-8') as f:
            questions = json.load(f)
        
        # Проверяем формат
        for q in questions:
            if 'question' not in q:
                raise ValueError("Вопрос не содержит поля 'question'")
            
            # Определяем тип вопроса если не указан
            if 'type' not in q:
                if 'options' in q:
                    q['type'] = 'multiple_choice' if 'correct_option' in q else 'multiple_select'
                else:
                    q['type'] = 'text'
        
        return questions
    
    except FileNotFoundError:
        # Если файла нет - создаём пример с вариантами ответов
        example_questions = [
            {
                "question": "Какая формула воды?",
                "answer": "H2O",
                "hint": "Подсказка: Два атома водорода и один кислорода",
                "type": "text"
            },
            {
                "question": "Столица Франции?",
                "options": ["Лондон", "Берлин", "Париж", "Рим"],
                "correct_option": 2,  # Индекс правильного ответа (начиная с 0)
                "hint": "Подсказка: Город с Эйфелевой башней",
                "type": "multiple_choice"
            },
            {
                "question": "Какие цвета есть в радуге? (Выберите все верные)",
                "options": ["Красный", "Синий", "Зеленый", "Фиолетовый"],
                "correct_options": [0, 2, 3],  # Индексы всех правильных ответов
                "hint": "Подсказка: ROYGBIV",
                "type": "multiple_select"
            }
        ]
        
        # Сохраняем пример
        with open('questions.json', 'w', encoding='utf-8') as f:
            json.dump(example_questions, f, ensure_ascii=False, indent=2)
        
        print("✅ Создан пример файла questions.json с вариантами ответов")
        return example_questions
    
    except Exception as e:
        print(f"❌ Ошибка при загрузке вопросов: {e}")
        # Резервные вопросы
        return [
            {
                "question": "Что это за ошибка?",
                "answer": "Нет вопросов",
                "hint": f"Подсказка: Проверьте файл questions.json. Ошибка: {str(e)}",
                "type": "text"
            }
        ]

# Загружаем вопросы при старте
QUESTIONS = load_questions()
# =======================================

# ====== ДОПОЛНИТЕЛЬНЫЕ ФИЛЬТРЫ JINJA2 ======
@app.template_filter('chr')
def ordinal_to_letter(n):
    """Преобразует число в букву: 1→A, 2→B, 3→C..."""
    return chr(64 + n) if 1 <= n <= 26 else str(n)
# =========================================

@app.route('/')
def start():
    """Сбрасываем прогресс при старте"""
    session['current_question'] = 0
    session['score'] = 0
    return redirect(url_for('question'))

@app.route('/question')
def question():
    """Показываем текущий вопрос"""
    current_q = session.get('current_question', 0)
    
    # Если вопросы закончились - показываем результат
    if current_q >= len(QUESTIONS):
        return render_template('result.html', 
                             score=session['score'], 
                             total=len(QUESTIONS))
    
    # Готовим данные для шаблона
    question_data = QUESTIONS[current_q]
    return render_template('question.html', 
                         question=question_data['question'],
                         question_num=current_q + 1,
                         total_questions=len(QUESTIONS),
                         question_type=question_data.get('type', 'text'),
                         options=question_data.get('options', []),
                         error=False)  # Добавляем параметр error по умолчанию

@app.route('/check', methods=['POST'])
def check_answer():
    """Проверяем ответ пользователя"""
    current_q = session.get('current_question', 0)
    if current_q >= len(QUESTIONS):
        return redirect(url_for('question'))
    
    question_data = QUESTIONS[current_q]
    question_type = question_data.get('type', 'text')
    is_correct = False
    
    try:
        if question_type == 'multiple_choice':
            # Обработка вопросов с одним вариантом ответа
            selected_option = request.form.get('option')
            if selected_option is None:
                # Не выбран ни один вариант
                return render_template('question.html',
                                     question=question_data['question'],
                                     question_num=current_q + 1,
                                     total_questions=len(QUESTIONS),
                                     error=True,
                                     hint="Пожалуйста, выберите один вариант ответа",
                                     options=question_data['options'],
                                     question_type=question_type)
            
            # Проверяем правильность ответа
            is_correct = int(selected_option) == question_data['correct_option']
        
        elif question_type == 'multiple_select':
            # Обработка вопросов с несколькими вариантами ответа
            selected_options = request.form.getlist('options')
            if not selected_options:
                # Не выбраны варианты
                return render_template('question.html',
                                     question=question_data['question'],
                                     question_num=current_q + 1,
                                     total_questions=len(QUESTIONS),
                                     error=True,
                                     hint="Пожалуйста, выберите хотя бы один вариант",
                                     options=question_data['options'],
                                     question_type=question_type)
            
            # Преобразуем выбранные варианты в числа и сортируем
            selected_indices = [int(opt) for opt in selected_options]
            correct_indices = question_data['correct_options']
            is_correct = sorted(selected_indices) == sorted(correct_indices)
        
        else:
            # Обработка текстовых вопросов
            user_answer = request.form['answer'].strip()
            correct_answer = question_data['answer'].strip()
            is_correct = user_answer.lower() == correct_answer.lower()
    
    except (ValueError, KeyError, TypeError) as e:
        print(f"Ошибка при проверке ответа: {e}")
        is_correct = False
    
    # === ЕДИНСТВЕННЫЙ БЛОК ОБРАБОТКИ РЕЗУЛЬТАТА ===
    if is_correct:
        # Правильный ответ - увеличиваем счет и переходим к следующему вопросу
        session['score'] = session.get('score', 0) + 1
        session['current_question'] = current_q + 1
        
        # Если вопросы закончились - показываем результат
        if session['current_question'] >= len(QUESTIONS):
            return redirect(url_for('question'))
        
        # Иначе переходим к следующему вопросу
        return redirect(url_for('question'))
    else:
        # Неправильный ответ - показываем подсказку на текущем вопросе
        return render_template('question.html',
                            question=question_data['question'],
                            question_num=current_q + 1,
                            total_questions=len(QUESTIONS),
                            error=True,
                            hint=question_data.get('hint', 'Попробуйте еще раз!'),
                            options=question_data.get('options', []),
                            question_type=question_type)

@app.route('/reset')
def reset():
    """Сбрасываем прогресс и начинаем заново"""
    session['current_question'] = 0
    session['score'] = 0
    return redirect(url_for('question'))

if __name__ == '__main__':
    # ВСЕГДА используй debug=False для публичного доступа!
    app.run(debug=True)
