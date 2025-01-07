from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from models import db, User, Doctor, MedicalRecord, Medication, MedicationReminder, Appointment, Message
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import pytz

app = Flask(__name__)
app.config['SECRET_KEY'] = '89d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///medical.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# إعداد البريد الإلكتروني
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your.medical.app@gmail.com'  # تحتاج لتغيير هذا لبريدك الإلكتروني
app.config['MAIL_PASSWORD'] = 'your-app-specific-password'  # تحتاج لتغيير هذا لكلمة المرور الخاصة بالتطبيق
app.config['MAIL_DEFAULT_SENDER'] = 'your.medical.app@gmail.com'  # تحتاج لتغيير هذا لبريدك الإلكتروني
db.init_app(app)
login_manager = LoginManager(app)
mail = Mail(app)
scheduler = BackgroundScheduler()
scheduler.timezone = pytz.timezone('Asia/Riyadh')  # تعيين المنطقة الزمنية للسعودية

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# قاعدة بيانات الأمراض
diseases_db = {
    "الصداع النصفي": {
        "symptoms": ["صداع شديد", "حساسية للضوء", "غثيان", "تقيؤ", "اضطرابات الرؤية", "دوار"],
        "risk_factors": ["التوتر", "قلة النوم", "بعض الأطعمة", "التغيرات الهرمونية", "الضوضاء"],
        "severity": "متوسط إلى شديد",
        "age_groups": ["البالغين", "المراهقين"],
        "treatment": "مسكنات الألم، تجنب المحفزات، الراحة في مكان مظلم وهادئ، العلاج الوقائي"
    },
    "التهاب الجيوب الأنفية": {
        "symptoms": ["احتقان الأنف", "صداع", "ألم في الوجه", "سيلان الأنف", "فقدان حاسة الشم", "سعال"],
        "risk_factors": ["الحساسية", "نزلات البرد", "التدخين", "ضعف المناعة"],
        "severity": "خفيف إلى متوسط",
        "age_groups": ["جميع الأعمار"],
        "treatment": "المضادات الحيوية، مضادات الاحتقان، غسل الأنف بالماء المالح، البخار"
    },
    "التهاب المعدة": {
        "symptoms": ["ألم في المعدة", "غثيان", "تقيؤ", "حرقة", "انتفاخ", "فقدان الشهية"],
        "risk_factors": ["الأطعمة الحارة", "القهوة", "التوتر", "الكحول", "الأدوية المضادة للالتهاب"],
        "severity": "متوسط",
        "age_groups": ["جميع الأعمار"],
        "treatment": "مضادات الحموضة، تعديل النظام الغذائي، تجنب المحفزات، الأدوية المضادة للالتهاب"
    },
    "ارتفاع ضغط الدم": {
        "symptoms": ["صداع", "دوخة", "ضيق في التنفس", "قلق", "نزيف من الأنف", "احمرار الوجه"],
        "risk_factors": ["التدخين", "السمنة", "قلة النشاط البدني", "التوتر", "تناول الملح بكثرة", "التاريخ العائلي"],
        "severity": "متوسط إلى شديد",
        "age_groups": ["كبار السن", "البالغين"],
        "treatment": "أدوية خفض الضغط، تعديل نمط الحياة، تقليل الملح، ممارسة الرياضة، الإقلاع عن التدخين"
    },
    "السكري": {
        "symptoms": ["العطش الشديد", "كثرة التبول", "التعب", "فقدان الوزن", "جوع مستمر", "تأخر التئام الجروح"],
        "risk_factors": ["السمنة", "قلة النشاط البدني", "التاريخ العائلي", "تناول السكريات بكثرة"],
        "severity": "شديد",
        "age_groups": ["جميع الأعمار"],
        "treatment": "الأنسولين، تعديل النظام الغذائي، ممارسة الرياضة، مراقبة مستوى السكر في الدم"
    },
    "التهاب المفاصل": {
        "symptoms": ["ألم في المفاصل", "تورم", "تيبس", "صعوبة في الحركة", "احمرار المفاصل", "ضعف العضلات"],
        "risk_factors": ["التقدم في العمر", "الإصابات السابقة", "الوراثة", "السمنة", "العمل الشاق"],
        "severity": "متوسط إلى شديد",
        "age_groups": ["كبار السن", "البالغين"],
        "treatment": "العلاج الطبيعي، الأدوية المضادة للالتهاب، التمارين الخفيفة، العلاج المائي"
    },
    "القولون العصبي": {
        "symptoms": ["ألم في البطن", "انتفاخ", "إسهال", "إمساك", "غازات", "تغير في حركة الأمعاء"],
        "risk_factors": ["التوتر", "بعض الأطعمة", "التغيرات الهرمونية", "الاضطرابات النفسية"],
        "severity": "خفيف إلى متوسط",
        "age_groups": ["البالغين", "المراهقين"],
        "treatment": "تعديل النظام الغذائي، إدارة التوتر، ممارسة الرياضة، الأدوية المهدئة للأمعاء"
    },
    "الأنفلونزا": {
        "symptoms": ["حمى", "سعال", "تعب", "آلام في الجسم", "صداع", "التهاب الحلق", "سيلان الأنف"],
        "risk_factors": ["موسم البرد", "ضعف المناعة", "الاختلاط بالمصابين", "عدم أخذ اللقاح"],
        "severity": "متوسط",
        "age_groups": ["جميع الأعمار"],
        "treatment": "الراحة، شرب السوائل، خافضات الحرارة، مضادات الفيروسات في الحالات الشديدة"
    },
    "حساسية الربيع": {
        "symptoms": ["عطس", "سيلان الأنف", "حكة في العين", "دموع", "احتقان الأنف", "ضيق في التنفس"],
        "risk_factors": ["موسم الربيع", "حبوب اللقاح", "التاريخ العائلي", "التلوث البيئي"],
        "severity": "خفيف إلى متوسط",
        "age_groups": ["جميع الأعمار"],
        "treatment": "مضادات الهيستامين، تجنب المحفزات، غسل الأنف، قطرات العين"
    },
    "التهاب اللوزتين": {
        "symptoms": ["ألم في الحلق", "صعوبة في البلع", "حمى", "تورم اللوزتين", "صداع", "تعب"],
        "risk_factors": ["التعرض للبرد", "العدوى البكتيرية", "ضعف المناعة", "التدخين"],
        "severity": "متوسط",
        "age_groups": ["الأطفال", "المراهقين", "البالغين"],
        "treatment": "المضادات الحيوية، مسكنات الألم، الغرغرة بالماء المالح، الراحة"
    },
    "التهاب المسالك البولية": {
        "symptoms": ["حرقة عند التبول", "تكرار التبول", "ألم في أسفل البطن", "تعكر البول", "تعب"],
        "risk_factors": ["قلة شرب الماء", "تأخير التبول", "النشاط الجنسي", "الحمل"],
        "severity": "متوسط",
        "age_groups": ["البالغين", "كبار السن"],
        "treatment": "المضادات الحيوية، شرب الكثير من الماء، مسكنات الألم"
    },
    "الربو": {
        "symptoms": ["ضيق في التنفس", "سعال", "صفير في الصدر", "ضيق في الصدر", "تعب"],
        "risk_factors": ["التاريخ العائلي", "الحساسية", "التدخين", "تلوث الهواء", "البرد"],
        "severity": "متوسط إلى شديد",
        "age_groups": ["جميع الأعمار"],
        "treatment": "موسعات الشعب الهوائية، مضادات الالتهاب، تجنب المحفزات، خطة علاج للطوارئ"
    },
    "التهاب الكبد": {
        "symptoms": ["اصفرار الجلد والعين", "تعب", "فقدان الشهية", "غثيان", "ألم في البطن", "حمى"],
        "risk_factors": ["العدوى الفيروسية", "الكحول", "الأدوية", "التاريخ العائلي"],
        "severity": "شديد",
        "age_groups": ["جميع الأعمار"],
        "treatment": "الراحة، النظام الغذائي الصحي، العلاج الدوائي حسب السبب"
    },
    "قرحة المعدة": {
        "symptoms": ["ألم في المعدة", "حرقة", "انتفاخ", "غثيان", "فقدان الشهية"],
        "risk_factors": ["التوتر", "الأدوية المضادة للالتهاب", "البكتيريا", "التدخين"],
        "severity": "متوسط إلى شديد",
        "age_groups": ["البالغين", "كبار السن"],
        "treatment": "مضادات الحموضة، المضادات الحيوية، تعديل النظام الغذائي"
    },
    "الاكتئاب": {
        "symptoms": ["حزن مستمر", "فقدان الاهتمام", "تغيرات في النوم", "تعب", "صعوبة التركيز"],
        "risk_factors": ["التاريخ العائلي", "التوتر", "الصدمات النفسية", "التغيرات الهرمونية"],
        "severity": "متوسط إلى شديد",
        "age_groups": ["جميع الأعمار"],
        "treatment": "العلاج النفسي، مضادات الاكتئاب، العلاج السلوكي المعرفي"
    }
}

def send_medication_reminder(user_email, medication_name):
    try:
        msg = Message('تذكير بالدواء',
                     recipients=[user_email])
        msg.body = f'تذكير: حان موعد تناول الدواء {medication_name}'
        mail.send(msg)
    except Exception as e:
        app.logger.error(f'خطأ في إرسال التذكير: {str(e)}')

def check_medication_reminders():
    with app.app_context():
        current_time = datetime.now(pytz.timezone('Asia/Riyadh'))
        reminders = MedicationReminder.query.join(Medication).join(MedicalRecord).join(User).filter(
            MedicationReminder.reminder_time <= current_time,
            MedicationReminder.is_sent == False
        ).all()
        
        for reminder in reminders:
            send_medication_reminder(reminder.medical_record.patient.email, reminder.medication.name)
            reminder.is_sent = True
            db.session.commit()

# إضافة مهمة التذكير للجدولة
scheduler.add_job(check_medication_reminders, 'interval', minutes=5)

def init_app():
    try:
        with app.app_context():
            db.create_all()
            scheduler.start()
    except Exception as e:
        app.logger.error(f'خطأ في تهيئة التطبيق: {str(e)}')

# تهيئة التطبيق عند بدء التشغيل
with app.app_context():
    init_app()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'البريد الإلكتروني مسجل مسبقاً'}), 400
        
        user = User(
            username=data['username'],
            email=data['email'],
            is_doctor=data.get('is_doctor', False)
        )
        user.set_password(data['password'])
        db.session.add(user)
        
        if user.is_doctor:
            doctor = Doctor(
                user_id=user.id,
                specialization=data['specialization'],
                experience_years=data['experience_years']
            )
            db.session.add(doctor)
            
        db.session.commit()
        login_user(user)
        return jsonify({'message': 'تم التسجيل بنجاح'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        user = User.query.filter_by(email=data['email']).first()
        if user and user.check_password(data['password']):
            login_user(user)
            return jsonify({'message': 'تم تسجيل الدخول بنجاح'})
        return jsonify({'error': 'البريد الإلكتروني أو كلمة المرور غير صحيحة'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'تم تسجيل الخروج بنجاح'})

@app.route('/add_medical_record', methods=['POST'])
@login_required
def add_medical_record():
    try:
        data = request.get_json()
        record = MedicalRecord(
            user_id=current_user.id,
            symptoms=data['symptoms'],
            diagnosis=data.get('diagnosis'),
            treatment=data.get('treatment'),
            notes=data.get('notes')
        )
        db.session.add(record)
        
        if 'medications' in data:
            for med_data in data['medications']:
                medication = Medication(
                    medical_record_id=record.id,
                    name=med_data['name'],
                    dosage=med_data['dosage'],
                    frequency=med_data['frequency'],
                    start_date=datetime.strptime(med_data['start_date'], '%Y-%m-%d'),
                    end_date=datetime.strptime(med_data['end_date'], '%Y-%m-%d') if med_data.get('end_date') else None
                )
                db.session.add(medication)
                
                # إضافة تذكيرات للدواء
                if med_data.get('reminders'):
                    for reminder_time in med_data['reminders']:
                        reminder = MedicationReminder(
                            medication_id=medication.id,
                            reminder_time=datetime.strptime(reminder_time, '%Y-%m-%d %H:%M')
                        )
                        db.session.add(reminder)
        
        db.session.commit()
        return jsonify({'message': 'تمت إضافة السجل الطبي بنجاح'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/appointments', methods=['GET', 'POST'])
@login_required
def appointments():
    if request.method == 'GET':
        if current_user.is_doctor:
            appointments = Appointment.query.filter_by(doctor_id=current_user.id).all()
        else:
            appointments = Appointment.query.filter_by(patient_id=current_user.id).all()
        return jsonify([{
            'id': apt.id,
            'date_time': apt.date_time.isoformat(),
            'status': apt.status,
            'notes': apt.notes
        } for apt in appointments])
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            appointment = Appointment(
                patient_id=current_user.id if not current_user.is_doctor else data['patient_id'],
                doctor_id=data['doctor_id'] if not current_user.is_doctor else current_user.id,
                date_time=datetime.strptime(data['date_time'], '%Y-%m-%d %H:%M'),
                notes=data.get('notes')
            )
            db.session.add(appointment)
            db.session.commit()
            return jsonify({'message': 'تم حجز الموعد بنجاح'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400

@app.route('/diagnose', methods=['POST'])
def diagnose():
    data = request.get_json()
    user_symptoms = [symptom.strip() for symptom in data['symptoms'].split('\n') if symptom.strip()]
    
    if not user_symptoms:
        return jsonify({'error': 'الرجاء إدخال الأعراض'}), 400

    results = []
    for disease_name, disease_info in diseases_db.items():
        matching_symptoms = [s for s in user_symptoms if s in disease_info['symptoms']]
        if matching_symptoms:
            match_percentage = (len(matching_symptoms) / len(disease_info['symptoms'])) * 100
            result = {
                'name': disease_name,
                'match_percentage': round(match_percentage, 1),
                'matching_symptoms': matching_symptoms,
                'all_symptoms': disease_info['symptoms'],
                'severity': disease_info['severity'],
                'risk_factors': disease_info['risk_factors'],
                'treatment': disease_info['treatment'],
                'age_groups': disease_info['age_groups']
            }
            results.append(result)
    
    # ترتيب النتائج حسب نسبة التطابق
    results.sort(key=lambda x: x['match_percentage'], reverse=True)
    
    return jsonify(results)

if __name__ == '__main__':
    try:
        app.run(debug=True)
    except Exception as e:
        app.logger.error(f'خطأ في تشغيل التطبيق: {str(e)}')
        scheduler.shutdown()