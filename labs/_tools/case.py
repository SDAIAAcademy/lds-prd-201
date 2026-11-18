"""Fixed facts of the case study: the Excavation Licences Service of Al-Nawwar City Municipality.

Everything here is fictional. The rules in SERVICE_RULES are the case's own rules, not a national
text. prepare_files.py turns these facts and texts.py into the files under labs/files/.
"""

SEED = 20271

ORG_AR = "أمانة مدينة النُّوّار"
SERVICE_AR = "خدمة تراخيص الحفر"

PEOPLE = [
    ("د. عبدالإله الشويعر", "وكيل الأمين للبنية التحتية، راعي الطلب"),
    ("هيفاء الدغيثر", "مديرة الخدمات الرقمية، ومديرة المشارك"),
    ("م. مشعل البقمي", "رئيس قسم تراخيص الحفر، ومالك بيانات التراخيص"),
    ("أروى الفهيد", "مشرفة مركز الاتصال"),
    ("بندر المحيميد", "رئيس فريق التفتيش الميداني"),
    ("نوف الرشودي", "مسؤولة حماية البيانات الشخصية"),
    ("تميم الصقعبي", "قائد الفريق الهندسي"),
]

# Licence types of the service (the case's own rules)
LICENCE_TYPES = {
    "T1": ("توصيل خدمة لعقار", "service connection to a property", 7),
    "T2": ("تمديد شبكة", "network extension", 30),
    "T3": ("قطع عرضي للطريق", "road crossing", 5),
    "T4": ("إصلاح طارئ", "emergency repair", 3),
}

# Return codes: Arabic meaning, English meaning, remedy in Arabic, remedy in English
RETURN_CODES = {
    "R1": ("مخطط الموقع غير معتمد من مكتب هندسي مرخّص",
           "site plan not stamped by a licensed engineering office",
           "ارفع مخطط الموقع بختم مكتب هندسي مرخّص وتوقيعه",
           "upload the site plan stamped and signed by a licensed engineering office"),
    "R2": ("خطة إدارة الحركة المرورية مفقودة أو ناقصة",
           "traffic management plan missing or incomplete",
           "أرفق خطة إدارة الحركة بمسار التحويلة وأوقات العمل واللوحات التحذيرية",
           "attach a traffic management plan with the detour, working hours and warning signs"),
    "R3": ("تعارض مع ترخيص قائم في الشارع نفسه",
           "clash with an existing licence on the same street",
           "انتظر تواصل القسم لتنسيق المواعيد مع صاحب الترخيص القائم، أو عدّل موقع العمل أو موعده",
           "wait for the section to coordinate dates with the existing licence holder, or change the location or dates"),
    "R4": ("ضمان إعادة السفلتة غير مرفق",
           "reinstatement guarantee not attached",
           "أرفق ضمان إعادة السفلتة بالمبلغ المحدد في نموذج الطلب",
           "attach the reinstatement guarantee for the amount stated on the application form"),
    "R5": ("خطاب عدم ممانعة من مالك الشبكة مفقود",
           "no-objection letter from the network owner missing",
           "أرفق خطاب عدم ممانعة ساري المفعول من مالك الشبكة",
           "attach a valid no-objection letter from the network owner"),
    "R6": ("المدة المطلوبة تتجاوز الحد الأقصى لنوع الترخيص",
           "requested duration exceeds the limit for the licence type",
           "قلّص المدة إلى الحد الأقصى لنوع الترخيص أو قسّم العمل على مراحل",
           "reduce the duration to the limit for the licence type or split the work into phases"),
    "R7": ("الشارع ضمن فترة حظر الحفر بعد سفلتة جديدة",
           "street under a digging moratorium after new paving",
           "اختر موعدًا بعد انتهاء فترة الحظر، أو قدّم طلب إصلاح طارئ إن كان العمل طارئًا فعلًا",
           "choose a date after the moratorium ends, or file an emergency repair if the work is truly an emergency"),
    "R8": ("بيانات المقاول لا تطابق سجل التصنيف",
           "contractor details do not match the classification register",
           "حدّث بيانات المقاول في الطلب لتطابق سجل التصنيف",
           "update the contractor details on the application to match the classification register"),
}

# Ticket categories: key, Arabic label, count in the 500 tickets, English share, applicant mix
CATEGORIES = [
    ("status", "الاستفسار عن حالة الطلب", 120, 0.30),
    ("returned", "سبب إعادة الطلب ونواقصه", 95, 0.35),
    ("extension", "تمديد مدة الترخيص", 55, 0.35),
    ("traffic", "خطة إدارة الحركة", 40, 0.40),
    ("guarantee", "استرداد ضمان السفلتة", 35, 0.30),
    ("emergency", "إصلاح طارئ", 30, 0.25),
    ("complaint", "شكوى ساكن من حفرية", 45, 0.05),
    ("clash", "تعارض مع ترخيص آخر", 25, 0.35),
    ("portal", "الدخول إلى البوابة", 30, 0.30),
    ("fine", "اعتراض على مخالفة", 25, 0.20),
]

# The contact centre's own tags (what agents pick); the true category is in the trainer's key only
AGENT_TAG = {
    "status": "حالة طلب", "returned": "نواقص وإعادة", "extension": "تمديد", "traffic": "خطة مرورية",
    "guarantee": "ضمان", "emergency": "طارئ", "complaint": "شكوى", "clash": "تعارض",
    "portal": "دخول البوابة", "fine": "مخالفة",
}

# Handling minutes (median of the generated draw) and reopen probability per category
HANDLING = {
    "status": (4, 0.06), "returned": (16, 0.34), "extension": (9, 0.12), "traffic": (14, 0.22),
    "guarantee": (11, 0.17), "emergency": (7, 0.10), "complaint": (12, 0.20), "clash": (18, 0.28),
    "portal": (6, 0.10), "fine": (8, 0.16),
}

# Cost of a wrong answer, the case's own reading (used in the trainer's key of lab 1.4)
COST_OF_ERROR = {
    "status": "منخفضة", "returned": "متوسطة", "extension": "متوسطة", "traffic": "متوسطة",
    "guarantee": "متوسطة", "emergency": "عالية", "complaint": "عالية", "clash": "متوسطة",
    "portal": "منخفضة", "fine": "عالية",
}

STREETS_AR = ["شارع السِّدر", "شارع الخزامى", "شارع الأرطى", "شارع الغَضا", "شارع العوسج",
              "شارع الشيح", "شارع العَرفج", "شارع الحُمّاض", "شارع الطلح", "شارع القرنفل"]
STREETS_EN = ["Al-Sidr Street", "Al-Khuzama Street", "Al-Arta Street", "Al-Ghadha Street",
              "Al-Awsaj Street", "Al-Shih Street", "Al-Arfaj Street", "Al-Hummad Street",
              "Al-Talh Street", "Al-Qaranfol Street"]
DISTRICTS_AR = ["حي الندى", "حي المروج", "حي الواحة", "حي الصفا", "حي الربوة", "حي النخيل"]

RESIDENT_FIRST = ["سلمى", "فهد", "منيرة", "ناصر", "عبير", "خالد", "هند", "سعد", "لطيفة", "ماجد",
                  "جواهر", "تركي", "ريم", "عمر", "دلال"]
RESIDENT_LAST = ["العتيبي", "الحربي", "القحطاني", "الشهري", "الزهراني", "الدوسري", "المطيري",
                 "الغامدي", "السبيعي", "العنزي"]

# The twelve requests of lab 1.1 and 1.2, with the reference class and cost of error.
# Classes: توليدي, تنبؤي, قواعد, دون أتمتة. The key is uneven on purpose (4, 2, 4, 2).
REQUESTS = [
    ("Q01", "مشرفة مركز الاتصال", "روبوت محادثة يجيب المتقدمين عن حالة طلباتهم بدل الاتصال بنا",
     "قواعد", "منخفضة", "الحالة حقل موجود في نظام التراخيص: استعلام وإشعار آلي يكفيان دون نموذج"),
    ("Q02", "رئيس قسم التراخيص", "مساعد يصوغ للموظف ردًا يشرح للمتقدم سبب إعادة طلبه وما ينقصه",
     "توليدي", "متوسطة", "صياغة نص بلغة المتقدم من رموز الإعادة وقواعدها، ويراجعه الموظف قبل الإرسال"),
    ("Q03", "وكيل الأمين", "معرفة الطلبات التي ستتجاوز مهلة المراجعة قبل أن تتجاوزها، فلدينا سجل عامين من الطلبات ومواعيد إنجازها",
     "تنبؤي", "منخفضة", "سجل عامين من الطلبات ونتائجها يكفي لنموذج تنبؤي، والخطأ يغير ترتيب العمل فقط"),
    ("Q04", "قسم المالية", "حساب رسوم الترخيص ومبلغ ضمان السفلتة آليًا",
     "قواعد", "متوسطة", "جدول رسوم ثابت وصيغة معروفة: حساب محدد لا يحتمل التقدير"),
    ("Q05", "شركات المرافق", "نموذج يقرر قبول تراخيص الإصلاح الطارئ أو رفضها",
     "دون أتمتة", "عالية", "قرار سلامة يتحمله المهندس المناوب، والحجم صغير، والإصلاح يبدأ بعد الإبلاغ"),
    ("Q06", "موظفو المراجعة", "استخراج اسم مالك الشبكة وتاريخ الخطاب ونطاقه من خطابات عدم الممانعة الممسوحة ضوئيًا",
     "توليدي", "متوسطة", "استخراج حقول من مستندات بصيغ مختلفة، ويتحقق الموظف من كل حقل"),
    ("Q07", "مشرفة مركز الاتصال", "توجيه التذاكر الواردة بالعربية والإنجليزية إلى الطابور الصحيح، مع أن وسوم الماضي غير موثوقة",
     "توليدي", "منخفضة", "تصنيف نص قصير بلغتين دون تاريخ موسوم موثوق، والخطأ يعيد التذكرة إلى طابور آخر"),
    ("Q08", "مشرفة مركز الاتصال", "توقع عدد التذاكر في الأسبوع القادم لجدولة المناوبات",
     "تنبؤي", "منخفضة", "سلسلة زمنية أسبوعية منتظمة، والخطأ يغير عدد الموظفين في مناوبة"),
    ("Q09", "رئيس قسم التراخيص", "فحص المدة المطلوبة مقابل حد نوع الترخيص، والشارع مقابل قائمة حظر الحفر، قبل وصول الطلب إلى الموظف",
     "قواعد", "متوسطة", "مقارنة رقم بحد وشارع بقائمة: قاعدة محددة نتيجتها نعم أو لا"),
    ("Q10", "رئيس فريق التفتيش", "تلخيص سلسلة رسائل شكوى الساكن في سطرين للمفتش قبل الزيارة",
     "توليدي", "عالية", "تلخيص نص حر، لكن الخطأ قد يخفي خطرًا: يقرأ المفتش النص الأصلي في حالات السلامة"),
    ("Q11", "رئيس قسم التراخيص", "تذكير المتقدم قبل انتهاء ترخيصه بثلاثة أيام",
     "قواعد", "منخفضة", "تاريخ الانتهاء معروف: رسالة مجدولة لا تحتاج نموذجًا"),
    ("Q12", "الإدارة القانونية", "نموذج يقرر قبول الاعتراضات على مخالفات الحفر أو رفضها",
     "دون أتمتة", "عالية", "قرار قانوني تملكه لجنة الاعتراضات، ويمس حقوق المعترض، وحجمه صغير"),
]

# Licence-system figures for the two months the tickets cover (the case's own system)
LICENCE_SYSTEM = [
    ("الطلبات المقدَّمة", 1236, 1302),
    ("الطلبات المعادة مرة واحدة على الأقل", 383, 388),
    ("الطلبات المعادة مرتين أو أكثر", 97, 92),
    ("وسيط أيام العمل حتى الترخيص، دون إعادة", 5, 5),
    ("وسيط أيام العمل حتى الترخيص، مع إعادة", 9, 10),
    ("بلاغات الإصلاح الطارئ", 61, 58),
    ("التراخيص السارية في آخر الشهر", 412, 437),
]

# The capstone feature: routing and summarising residents' trench complaints
CAPSTONE_ROUTES = {
    "C1": "إحالة عاجلة إلى فريق التفتيش الميداني (خطر على السلامة)",
    "C2": "إحالة إلى فريق التفتيش لزيارة مجدولة (مخالفة اشتراطات دون خطر قائم)",
    "C3": "إحالة إلى صاحب الترخيص عبر القسم (إزعاج أو تأخر في الإغلاق ضمن المدة)",
    "C4": "رد معلوماتي دون إحالة (سؤال عن مدة العمل أو جهته)",
}

CONSTRAINT_CARDS = [
    ("K1", "قررت مالكة البيانات ألا يخرج نص الشكوى إلى أي خدمة مستضافة، ولو بعد الحذف: يُرسَل الموقع ونوع الملاحظة فقط."),
    ("K2", "فريق التفتيش يستقبل الإحالات في أيام العمل فقط، من الثامنة صباحًا حتى الرابعة عصرًا."),
    ("K3", "يريد الوكيل أن تُرسَل الردود المعلوماتية (المسار C4) إلى الساكن دون مراجعة موظف."),
    ("K4", "ثلث الشكاوى الجديدة تصل رسائلَ صوتية من الهاتف، لا نصًّا مكتوبًا."),
]
