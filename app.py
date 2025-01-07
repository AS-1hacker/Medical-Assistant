from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from functools import wraps
import logging

app = Flask(__name__)
CORS(app)

# تكوين التطبيق
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# إعداد قاعدة البيانات
db = SQLAlchemy(app)

# نماذج قاعدة البيانات
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())

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
    """
}

@app.before_first_request
def create_tables():
    # إنشاء المجلدات المطلوبة
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    
    # إنشاء جداول قاعدة البيانات
    db.create_all()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
        
        if not username or not password:
            flash('جميع الحقول مطلوبة')
            return redirect(url_for('register'))
        
        if User.query.filter_by(username=username).first():
            flash('اسم المستخدم موجود بالفعل')
            return redirect(url_for('register'))
        
        user = User(
            username=username,
            password=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        
        flash('تم إنشاء الحساب بنجاح')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not check_password_hash(user.password, password):
            flash('اسم المستخدم أو كلمة المرور غير صحيحة')
            return redirect(url_for('login'))
        
        session['user_id'] = user.id
        session['username'] = user.username
        return redirect(url_for('index'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/send_message', methods=['POST'])
@login_required
def send_message():
    message = request.json.get('message')
    if not message:
        return jsonify({'error': 'لا توجد رسالة'}), 400
    
    # حفظ الرسالة في قاعدة البيانات
    new_message = Message(
        user_id=session['user_id'],
        content=message
    )
    db.session.add(new_message)
    db.session.commit()
    
    # إرسال الرد
    response = get_medical_response(message)
    return jsonify({'response': response})

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
        medication_name = "بانادول"
        
        medication_info = get_medication_info(medication_name)
        return jsonify({
            'response': medication_info,
            'filename': filename
        })
    
    return jsonify({'error': 'نوع الملف غير مسموح به'}), 400

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

@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error='الصفحة غير موجودة'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    app.logger.error(f'Server Error: {error}')
    return render_template('error.html', error='حدث خطأ في الخادم'), 500

if __name__ == '__main__':
    # إعداد التسجيل
    logging.basicConfig(level=logging.INFO)
    app.logger.setLevel(logging.INFO)
    
    # تشغيل التطبيق
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
