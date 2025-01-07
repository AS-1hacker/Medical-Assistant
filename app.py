from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key')

# تكوين مجلد الصور
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# قاموس معلومات الأدوية
medications_info = {
    'بانادول': {
        'الاسم_العلمي': 'باراسيتامول',
        'الاستخدامات': [
            'تخفيف الألم الخفيف إلى المتوسط',
            'خفض الحرارة',
            'علاج الصداع'
        ],
        'طريقة_الاستخدام': 'قرص أو قرصين كل 6 ساعات حسب الحاجة. لا تتجاوز 8 أقراص في اليوم.',
        'الآثار_الجانبية': [
            'نادرة مع الاستخدام الصحيح',
            'قد تشمل مشاكل في الكبد مع الجرعات العالية'
        ],
        'تحذيرات': 'استشر الطبيب إذا استمر الألم لأكثر من 3 أيام'
    },
    'بروفين': {
        'الاسم_العلمي': 'ايبوبروفين',
        'الاستخدامات': [
            'مسكن للألم',
            'مضاد للالتهابات',
            'خافض للحرارة'
        ],
        'طريقة_الاستخدام': 'قرص واحد (400 ملغ) كل 6-8 ساعات بعد الطعام',
        'الآثار_الجانبية': [
            'قد يسبب مشاكل في المعدة',
            'صداع خفيف',
            'دوخة'
        ],
        'تحذيرات': 'تجنب الاستخدام على معدة فارغة'
    }
}

# قاموس الردود الطبية
medical_responses = {
    'الم المعدة': """
    فيما يتعلق بألم المعدة، هناك عدة نصائح وإرشادات:

    الأسباب المحتملة:
    1. عسر الهضم
    2. التهاب المعدة
    3. القرحة المعدية
    4. الإجهاد والتوتر

    النصائح الأولية:
    1. تناول وجبات صغيرة ومتعددة
    2. تجنب الأطعمة الحارة والدهنية
    3. شرب الماء بكميات كافية
    4. تجنب الاستلقاء مباشرة بعد الأكل

    العلاجات المقترحة:
    1. أدوية مضادات الحموضة
    2. شاي البابونج أو النعناع
    3. بروبيوتيك لتحسين الهضم
    4. تناول الزنجبيل الطازج

    متى يجب زيارة الطبيب:
    - إذا استمر الألم لأكثر من يومين
    - إذا كان الألم شديداً
    - إذا صاحب الألم قيء أو إسهال
    """,
    
    'صداع': """
    بخصوص الصداع، إليك المعلومات الضرورية:

    الأسباب الشائعة:
    1. التوتر والإجهاد
    2. قلة النوم
    3. الجفاف
    4. مشاكل في النظر

    النصائح الأولية:
    1. أخذ قسط كافٍ من الراحة
    2. شرب الماء بكميات كافية
    3. تجنب الضوء القوي والضوضاء
    4. تدليك خفيف للرأس والرقبة

    العلاجات المقترحة:
    1. مسكنات الألم مثل:
       - باراسيتامول (بانادول)
       - ايبوبروفين (بروفين)
    2. كمادات باردة أو دافئة
    3. زيوت عطرية للتدليك

    متى تزور الطبيب:
    - صداع شديد ومفاجئ
    - صداع مصحوب بحمى
    - صداع يمنعك من ممارسة حياتك اليومية
    """
}

def get_db():
    db = sqlite3.connect('database.db')
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with app.app_context():
        db = get_db()
        with open('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_medication_info(medication_name):
    if medication_name in medications_info:
        info = medications_info[medication_name]
        uses = '\n'.join([f"- {use}" for use in info['الاستخدامات']])
        side_effects = '\n'.join([f"- {effect}" for effect in info['الآثار_الجانبية']])
        
        response = f"""معلومات عن {medication_name}:

الاسم العلمي: {info['الاسم_العلمي']}

الاستخدامات:
{uses}

طريقة الاستخدام:
{info['طريقة_الاستخدام']}

الآثار الجانبية:
{side_effects}

تحذيرات مهمة:
{info['تحذيرات']}"""
        return response
    return "عذراً، لا تتوفر معلومات عن هذا الدواء"

def get_medical_response(message):
    message = message.strip()
    for keyword, response in medical_responses.items():
        if keyword in message:
            return response
    return """
    مرحباً! أنا المساعد الطبي الخاص بك. كيف يمكنني مساعدتك؟
    
    يمكنني تقديم معلومات عن:
    - الأعراض الشائعة
    - النصائح الطبية العامة
    - الإسعافات الأولية
    - متى يجب زيارة الطبيب
    
    الرجاء وصف ما تشعر به بالتفصيل.
    """

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    return render_template('index.html', username=session.get('username'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db()
        error = None

        if not username:
            error = 'اسم المستخدم مطلوب'
        elif not password:
            error = 'كلمة المرور مطلوبة'
        elif db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone() is not None:
            error = 'المستخدم {} موجود بالفعل'.format(username)

        if error is None:
            db.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                      (username, generate_password_hash(password)))
            db.commit()
            return redirect(url_for('login'))

        flash(error)

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db()
        error = None
        
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()

        if user is None:
            error = 'اسم المستخدم غير صحيح'
        elif not check_password_hash(user['password'], password):
            error = 'كلمة المرور غير صحيحة'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('index'))

        flash(error)

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/send_message', methods=['POST'])
@login_required
def send_message():
    message = request.json.get('message')
    if message:
        response = get_medical_response(message)
        return jsonify({'response': response})
    return jsonify({'error': 'لا توجد رسالة'}), 400

@app.route('/upload_image', methods=['POST'])
@login_required
def upload_image():
    if 'file' not in request.files:
        return jsonify({'error': 'لم يتم إرسال صورة'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'لم يتم اختيار صورة'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # هنا يمكن إضافة خوارزمية للتعرف على الدواء من الصورة
        # حالياً سنفترض أنه بانادول كمثال
        medication_name = "بانادول"
        
        medication_info = get_medication_info(medication_name)
        return jsonify({
            'response': medication_info,
            'filename': filename
        })
    
    return jsonify({'error': 'نوع الملف غير مسموح به'}), 400

if __name__ == '__main__':
    if not os.path.exists('database.db'):
        init_db()
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
