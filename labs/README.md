# استكشاف منتجات الذكاء الاصطناعي وإعداد مواصفاتها: المختبرات

اثنا عشر مختبرًا لمقرر أكاديمية سدايا **LDS-PRD-201**، مدة كل منها 35 دقيقة. المختبرات صفحات إرشادية بالعربية: ما
تخرج به، والملفات، وخطوات بدقائقها، وأسئلة تحقق، وتمرين إضافي ✱، ومفتاح للمدرب. لا كود يكتبه المشارك، ولا نموذج
يُنزَّل على جهازه، ولا مفتاح حساب يلزمه ليكمل أي مختبر.

كل المختبرات في جهة واحدة: **خدمة تراخيص الحفر في أمانة مدينة الرِّمرام**، جهة افتراضية. كل الأشخاص والمقابلات
والتذاكر والأرقام اصطناعية، تولدها `_tools/prepare_files.py` ببذرة ثابتة. قواعد الخدمة وقاعدة الأمانة في إرسال
البيانات إلى الأدوات التوليدية من وضع الحالة، لا نصوص نظامية.

## ما يحتاجه المشارك

- جدول بيانات يفتح ملفات `xlsx` بالعربية: LibreOffice Calc أو Microsoft Excel أو Google Sheets. القوائم المنسدلة
  والمعادلات في الملفات (ورقة «الاتفاق» في 3.2، وورقة «التغطية» في 3.3) كتبها المولّد ولم تُجرَّب في كل برنامج؛
  أرقامها المرجعية يحسبها `solutions/check.py`.
- للنموذج الأولي في اليوم الثاني طريق واحد من ثلاثة:
  - **السكربت على الجهاز:** `uv run run_prototype.py` في مجلد `prototype/`. سكربت واحد بمكتبة بايثون القياسية، لا
    يثبّت شيئًا.
  - **Colab:** يُرفع مجلد `labs` كما هو، ثم `!cd labs/prototype && python run_prototype.py ...` في خلية.
  - **مساعد محادثة** معتمد في جهة المشارك أو بخطة مجانية، والنتائج في `files/prototype_log.xlsx`.

## النموذج المستضاف والبديل المبرمج

السكربت يقرأ `LLM_BASE_URL` و`LLM_MODEL` و`LLM_API_KEY` من البيئة أو من ملف `.env` في `prototype/`، والمثال في
`prototype/.env.example`: OpenRouter ونموذج `google/gemma-4-31b-it:free` (موجود في قائمة النماذج في 18 نوفمبر 2026).
حدود نماذج `:free` في OpenRouter في التاريخ نفسه: 20 طلبًا في الدقيقة، و50 في اليوم لمن اشترى أقل من 10 أرصدة
(credits) منذ فتح حسابه، و1000 لمن اشترى 10 فأكثر. اليوم الثاني نحو 40 طلبًا للمشارك، والسكربت يحفظ كل إجابة في
`prototype/runs/cache.json` فلا تُطلب الحالة نفسها بالأمر نفسه مرتين. النماذج المجانية تتغير كثيرًا: إن غاب النموذج
فاختر نموذجًا آخر ينتهي اسمه بـ `:free`.

دون الإعدادات الثلاثة، أو مع `--standin`، يجيب **بديل مبرمج**: برنامج قصير وليس نموذجًا لغويًا، نقاط ضعفه مكتوبة في
السكربت، ولا يقرأ الأمر. يقول ذلك في أول سطر من تشغيله، وفي ملف `runs/<label>.json`، وفي عمود `answers_from` من كل
سجل. السجلات المرجعية الثلاثة (`prototype/prototype_log_reference.csv` و`prototype/prototype_log_graded.csv`
و`files/capstone/complaints_log_reference.csv`) من هذا البديل، وكل رقم منها يصف البديل وحده. لم يُشغَّل أي نموذج
لغوي في إعداد المقرر.

## نقطة البداية والحل

كل مختبر يبدأ من ملفات في `files/` أو `prototype/`. المختبر الذي يكمل عمل مختبر سابق له نقطة بداية بديلة لمن لم يكمل.

| المختبر | الصفحة | يبدأ من | الحل المرجعي |
|---|---|---|---|
| 1.1 | `D1_1_outcomes.html` | `case_brief.txt`، `requests_12.xlsx`، `service_baseline.xlsx` | `solutions/D1_1_outcomes.md` |
| 1.2 | `D1_2_triage.html` | `requests_12.xlsx` (الفارغ بديل)، `service_rules.txt` | `solutions/D1_2_triage.md`، `reference/lab_1_2.json` |
| 1.3 | `D1_3_interviews.html` | `interviews.txt`، `affinity_sheet.xlsx` | `solutions/D1_3_interviews.md` |
| 1.4 | `D1_4_tickets.html` | `tickets.xlsx` أو `tickets.csv` | `solutions/D1_4_tickets.md`، `reference/figures.json` |
| 2.1 | `D2_1_opportunity_map.html` | `opportunity_map.xlsx`، `ai_synthesis.txt`، ورقة التقارب المرجعية في حل 1.3 (بديل) | `solutions/D2_1_opportunity_map.md`، `reference/lab_2_1.json` |
| 2.2 | `D2_2_first_prompt.html` | `run_prototype.py`، `prompt_starter.txt`، `demo_5.csv` | `solutions/D2_2_first_prompt.md`، `reference/prompt_v2.txt` |
| 2.3 | `D2_3_thirty_cases.html` | `cases_30.csv`، أو `prototype_log_reference.csv` (بديل) | `solutions/D2_3_thirty_cases.md`، `reference/lab_2_3.json` |
| 2.4 | `D2_4_feasibility_note.html` | `prototype_log_graded.csv`، `feasibility_note_template.md` | `solutions/D2_4_feasibility_note.md` |
| 3.1 | `D3_1_behaviour_spec.html` | `spec_template.md`، `service_rules.txt`، `cases_30.csv` | `solutions/D3_1_behaviour_spec.md` |
| 3.2 | `D3_2_criteria.html` | `spec_colleague_draft.md`، `ten_outputs.xlsx` | `solutions/D3_2_criteria.md`، `reference/lab_3_2.json` |
| 3.3 | `D3_3_eval_set.html` | `eval_candidates.xlsx` | `solutions/D3_3_eval_set.md`، `reference/lab_3_3.json` |
| 3.4 | `D3_4_data_needs.html` | `data_sources.xlsx`، `data_needs_template.md`، `capstone/capstone_brief.txt` | `solutions/D3_4_data_needs.md`، `reference/lab_3_4.json` |

ملفات المشروع الختامي في `files/capstone/`.

## للمدرب

- `uv run labs/solutions/check.py` يعيد حساب كل رقم مرجعي من الملفات، ويعيد تشغيل البديل المبرمج على الحالات، ويطبع
  `ALL PASS` أو أول اختلاف. مكتبة بايثون القياسية وحدها.
- `uv run labs/_tools/figures.py` يطبع الأرقام التي تذكرها الشرائح والملاحظات والحلول.
- `uv run labs/_tools/prepare_files.py` يعيد كتابة كل الملفات من البذرة الثابتة (يحتاج `openpyxl`، ويثبّته `uv` في
  بيئة مؤقتة).
- المختبرات المقيَّمة وتصحيحها في «للمقيِّم» آخر كل حل مرجعي. أحكام 2.3 لا تدخل الدرجة، لأن السجل المحكوم ملف بداية
  2.4 ومنشور معه؛ الناتج المقيَّم مذكرة 2.4.
