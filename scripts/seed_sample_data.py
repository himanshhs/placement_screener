import sys, os, json
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models.models import db, Student, Resume, GitHubSignal, CPSignal, Drive, DriveScore

app = create_app()

STUDENTS = [
    {"erp_id":"CS2021001","name":"Himanshu Patil","email":"himanshu@college.edu","branch":"CSE","year":3,"cgpa":9.1,"backlogs":0,"tenth_pct":94.2,"twelfth_pct":91.0,"github_url":"https://github.com/himanshu","leetcode_user":"himanshu_lc","codeforces_user":"himanshu_cf","is_startup_founder":True,"has_ml_internship":False,"has_open_source":False,
     "gh":{"total_repos":18,"total_commits_90d":87,"unique_languages":5,"has_readme_projects":True,"longest_streak_days":28,"days_since_last_commit":3,"github_score":82.5},
     "cp":{"lc_solved_easy":45,"lc_solved_medium":98,"lc_solved_hard":22,"lc_contest_rating":1820.0,"lc_contests_attended":14,"lc_avg_attempts_per_problem":2.1,"cf_rating":1450,"cf_max_rating":1512,"cf_contests_attended":18,"cf_problems_solved":210,"cc_rating":1680,"cc_problems_solved":95,"authenticity_score":0.98,"flag_suspicious":False,"flag_reason":"no issues detected","cp_score":74.3},
     "res":{"raw_skills":"Python machine learning Flask React Node.js PostgreSQL Docker AWS Git","raw_projects":"Built AI resume screening tool using SBERT. Developed real-time chat app. Created portfolio tracker.","raw_internships":"Machine Learning Intern at TechCorp Pune June 2023. NLP pipeline for document classification.","raw_experience":"Freelance web developer 8 months. Built 3 client websites.","raw_certifications":"AWS Cloud Practitioner. Google Python Certificate. Deep Learning Specialization.","raw_education":"B.Tech CSE CGPA 9.1. 12th 91%. 10th 94.2%."}},

    {"erp_id":"CS2021002","name":"Priya Sharma","email":"priya@college.edu","branch":"CSE","year":3,"cgpa":8.7,"backlogs":0,"tenth_pct":89.0,"twelfth_pct":85.5,"github_url":"https://github.com/priya","leetcode_user":"priya_lc","codeforces_user":"priya_cf","is_startup_founder":False,"has_ml_internship":True,"has_open_source":False,
     "gh":{"total_repos":12,"total_commits_90d":54,"unique_languages":4,"has_readme_projects":True,"longest_streak_days":18,"days_since_last_commit":7,"github_score":68.2},
     "cp":{"lc_solved_easy":60,"lc_solved_medium":75,"lc_solved_hard":8,"lc_contest_rating":1540.0,"lc_contests_attended":9,"lc_avg_attempts_per_problem":1.8,"cf_rating":1200,"cf_max_rating":1280,"cf_contests_attended":11,"cf_problems_solved":145,"cc_rating":1450,"cc_problems_solved":70,"authenticity_score":0.95,"flag_suspicious":False,"flag_reason":"no issues detected","cp_score":58.7},
     "res":{"raw_skills":"Python TensorFlow Keras scikit-learn Pandas NumPy SQL Tableau","raw_projects":"Sentiment analysis 92% accuracy. Image classification CNN. Data dashboard for placement.","raw_internships":"Data Science Intern Analytics India May 2023. Predictive models for churn.","raw_experience":"","raw_certifications":"IBM Data Science Certificate. TensorFlow Developer Certificate.","raw_education":"B.Tech CSE CGPA 8.7. 12th 85.5%. 10th 89%."}},

    {"erp_id":"IT2021003","name":"Rahul Deshmukh","email":"rahul@college.edu","branch":"IT","year":3,"cgpa":7.4,"backlogs":1,"tenth_pct":78.0,"twelfth_pct":72.0,"github_url":"https://github.com/rahul","leetcode_user":"rahul_lc","codeforces_user":"","is_startup_founder":False,"has_ml_internship":False,"has_open_source":False,
     "gh":{"total_repos":6,"total_commits_90d":12,"unique_languages":2,"has_readme_projects":False,"longest_streak_days":5,"days_since_last_commit":45,"github_score":22.1},
     "cp":{"lc_solved_easy":120,"lc_solved_medium":115,"lc_solved_hard":0,"lc_contest_rating":0.0,"lc_contests_attended":0,"lc_avg_attempts_per_problem":1.02,"cf_rating":0,"cf_max_rating":0,"cf_contests_attended":0,"cf_problems_solved":0,"cc_rating":0,"cc_problems_solved":0,"authenticity_score":0.38,"flag_suspicious":True,"flag_reason":"avg attempts/problem=1.02; no contest participation; zero hard problems","cp_score":14.2},
     "res":{"raw_skills":"Java Python HTML CSS JavaScript MySQL","raw_projects":"Simple to-do app Java. College website redesign.","raw_internships":"","raw_experience":"","raw_certifications":"","raw_education":"B.Tech IT CGPA 7.4 backlog 1. 12th 72%. 10th 78%."}},

    {"erp_id":"CS2021004","name":"Sneha Kulkarni","email":"sneha@college.edu","branch":"CSE","year":3,"cgpa":9.4,"backlogs":0,"tenth_pct":96.8,"twelfth_pct":93.2,"github_url":"https://github.com/sneha","leetcode_user":"sneha_lc","codeforces_user":"sneha_cf","is_startup_founder":False,"has_ml_internship":False,"has_open_source":True,
     "gh":{"total_repos":24,"total_commits_90d":112,"unique_languages":7,"has_readme_projects":True,"longest_streak_days":42,"days_since_last_commit":1,"github_score":91.0},
     "cp":{"lc_solved_easy":80,"lc_solved_medium":180,"lc_solved_hard":65,"lc_contest_rating":2150.0,"lc_contests_attended":28,"lc_avg_attempts_per_problem":2.6,"cf_rating":1820,"cf_max_rating":1950,"cf_contests_attended":32,"cf_problems_solved":380,"cc_rating":1920,"cc_problems_solved":160,"authenticity_score":1.0,"flag_suspicious":False,"flag_reason":"no issues detected","cp_score":94.1},
     "res":{"raw_skills":"C++ Python Java algorithms data structures system design distributed systems competitive programming","raw_projects":"Contributed to open source compiler. Distributed key-value store. Custom memory allocator C++.","raw_internships":"Software Engineering Intern Google Bangalore May 2023. Search infrastructure team.","raw_experience":"Open source contributor Apache 120 merged PRs.","raw_certifications":"Google Cloud Professional. ACM ICPC Regionalist 2023.","raw_education":"B.Tech CSE CGPA 9.4. 12th 93.2%. 10th 96.8%."}},

    {"erp_id":"ECE2021005","name":"Arjun Nair","email":"arjun@college.edu","branch":"ECE","year":3,"cgpa":8.2,"backlogs":0,"tenth_pct":88.0,"twelfth_pct":82.0,"github_url":"https://github.com/arjun","leetcode_user":"arjun_lc","codeforces_user":"","is_startup_founder":False,"has_ml_internship":False,"has_open_source":False,
     "gh":{"total_repos":9,"total_commits_90d":38,"unique_languages":3,"has_readme_projects":True,"longest_streak_days":14,"days_since_last_commit":12,"github_score":51.3},
     "cp":{"lc_solved_easy":55,"lc_solved_medium":60,"lc_solved_hard":5,"lc_contest_rating":1380.0,"lc_contests_attended":6,"lc_avg_attempts_per_problem":1.65,"cf_rating":900,"cf_max_rating":980,"cf_contests_attended":5,"cf_problems_solved":88,"cc_rating":1200,"cc_problems_solved":45,"authenticity_score":0.92,"flag_suspicious":False,"flag_reason":"no issues detected","cp_score":38.9},
     "res":{"raw_skills":"Embedded C Python MATLAB IoT Raspberry Pi Arduino signal processing","raw_projects":"Smart home automation Raspberry Pi. IoT air quality monitor. MATLAB digital filters.","raw_internships":"Embedded Systems Intern Bosch India June 2023.","raw_experience":"","raw_certifications":"NPTEL IoT Certificate. Embedded Systems Coursera.","raw_education":"B.Tech ECE CGPA 8.2. 12th 82%. 10th 88%."}},

    {"erp_id":"CS2021006","name":"Tanvi Joshi","email":"tanvi@college.edu","branch":"CSE","year":3,"cgpa":8.9,"backlogs":0,"tenth_pct":91.5,"twelfth_pct":88.0,"github_url":"https://github.com/tanvi","leetcode_user":"tanvi_lc","codeforces_user":"tanvi_cf","is_startup_founder":False,"has_ml_internship":False,"has_open_source":False,
     "gh":{"total_repos":15,"total_commits_90d":65,"unique_languages":5,"has_readme_projects":True,"longest_streak_days":22,"days_since_last_commit":5,"github_score":74.8},
     "cp":{"lc_solved_easy":70,"lc_solved_medium":120,"lc_solved_hard":18,"lc_contest_rating":1720.0,"lc_contests_attended":16,"lc_avg_attempts_per_problem":2.0,"cf_rating":1350,"cf_max_rating":1420,"cf_contests_attended":14,"cf_problems_solved":195,"cc_rating":1600,"cc_problems_solved":85,"authenticity_score":0.97,"flag_suspicious":False,"flag_reason":"no issues detected","cp_score":66.4},
     "res":{"raw_skills":"Python Java Spring Boot microservices REST API Kafka Redis Docker Kubernetes","raw_projects":"E-commerce microservices Spring Boot. Real-time notifications Kafka. Deployed AWS EKS.","raw_internships":"Backend Developer Intern Flipkart May 2023.","raw_experience":"","raw_certifications":"AWS Solutions Architect Associate. Kubernetes CKA.","raw_education":"B.Tech CSE CGPA 8.9. 12th 88%. 10th 91.5%."}},

    {"erp_id":"AIDS2021007","name":"Rohit Mehta","email":"rohit@college.edu","branch":"AIDS","year":3,"cgpa":7.8,"backlogs":0,"tenth_pct":82.0,"twelfth_pct":78.5,"github_url":"https://github.com/rohit","leetcode_user":"rohit_lc","codeforces_user":"","is_startup_founder":False,"has_ml_internship":False,"has_open_source":False,
     "gh":{"total_repos":8,"total_commits_90d":29,"unique_languages":3,"has_readme_projects":True,"longest_streak_days":10,"days_since_last_commit":18,"github_score":43.2},
     "cp":{"lc_solved_easy":85,"lc_solved_medium":45,"lc_solved_hard":2,"lc_contest_rating":1180.0,"lc_contests_attended":4,"lc_avg_attempts_per_problem":1.55,"cf_rating":0,"cf_max_rating":0,"cf_contests_attended":0,"cf_problems_solved":0,"cc_rating":1100,"cc_problems_solved":30,"authenticity_score":0.88,"flag_suspicious":False,"flag_reason":"no issues detected","cp_score":28.6},
     "res":{"raw_skills":"Python R machine learning data analysis Power BI Excel statistics regression","raw_projects":"Sales forecasting model retail. Customer segmentation K-means. Power BI HR dashboard.","raw_internships":"Data Analyst Intern Deloitte June 2023.","raw_experience":"","raw_certifications":"Microsoft Power BI Analyst. Google Data Analytics Certificate.","raw_education":"B.Tech AIDS CGPA 7.8. 12th 78.5%. 10th 82%."}},

    {"erp_id":"CS2021008","name":"Aditya Bhosale","email":"aditya@college.edu","branch":"CSE","year":3,"cgpa":6.9,"backlogs":2,"tenth_pct":74.0,"twelfth_pct":69.0,"github_url":"https://github.com/aditya","leetcode_user":"aditya_lc","codeforces_user":"","is_startup_founder":False,"has_ml_internship":False,"has_open_source":False,
     "gh":{"total_repos":4,"total_commits_90d":8,"unique_languages":2,"has_readme_projects":False,"longest_streak_days":3,"days_since_last_commit":62,"github_score":12.4},
     "cp":{"lc_solved_easy":200,"lc_solved_medium":180,"lc_solved_hard":0,"lc_contest_rating":0.0,"lc_contests_attended":0,"lc_avg_attempts_per_problem":1.01,"cf_rating":0,"cf_max_rating":0,"cf_contests_attended":0,"cf_problems_solved":0,"cc_rating":0,"cc_problems_solved":0,"authenticity_score":0.28,"flag_suspicious":True,"flag_reason":"avg attempts/problem=1.01; no contest participation; zero hard problems","cp_score":5.1},
     "res":{"raw_skills":"HTML CSS JavaScript PHP MySQL","raw_projects":"College notice board website. Basic calculator app.","raw_internships":"","raw_experience":"","raw_certifications":"","raw_education":"B.Tech CSE CGPA 6.9 backlogs 2. 12th 69%. 10th 74%."}},

    {"erp_id":"AIML2021009","name":"Pooja Reddy","email":"pooja@college.edu","branch":"AIML","year":3,"cgpa":9.0,"backlogs":0,"tenth_pct":95.0,"twelfth_pct":90.0,"github_url":"https://github.com/pooja","leetcode_user":"pooja_lc","codeforces_user":"pooja_cf","is_startup_founder":False,"has_ml_internship":True,"has_open_source":False,
     "gh":{"total_repos":20,"total_commits_90d":95,"unique_languages":6,"has_readme_projects":True,"longest_streak_days":35,"days_since_last_commit":2,"github_score":88.4},
     "cp":{"lc_solved_easy":55,"lc_solved_medium":110,"lc_solved_hard":30,"lc_contest_rating":1950.0,"lc_contests_attended":20,"lc_avg_attempts_per_problem":2.3,"cf_rating":1600,"cf_max_rating":1720,"cf_contests_attended":22,"cf_problems_solved":280,"cc_rating":1750,"cc_problems_solved":110,"authenticity_score":1.0,"flag_suspicious":False,"flag_reason":"no issues detected","cp_score":82.7},
     "res":{"raw_skills":"Python PyTorch TensorFlow computer vision NLP transformers BERT GPT Hugging Face fine-tuning","raw_projects":"Fine-tuned LLM legal document summarization. Object detection pipeline. Research paper transformers.","raw_internships":"ML Research Intern Microsoft Research May 2023. Published 1 paper.","raw_experience":"Teaching Assistant Machine Learning course.","raw_certifications":"Deep Learning Specialization. NLP Specialization Coursera.","raw_education":"B.Tech AIML CGPA 9.0. 12th 90%. 10th 95%."}},

    {"erp_id":"IT2021010","name":"Karan Singhania","email":"karan@college.edu","branch":"IT","year":3,"cgpa":8.4,"backlogs":0,"tenth_pct":86.0,"twelfth_pct":81.0,"github_url":"https://github.com/karan","leetcode_user":"karan_lc","codeforces_user":"karan_cf","is_startup_founder":False,"has_ml_internship":False,"has_open_source":False,
     "gh":{"total_repos":11,"total_commits_90d":48,"unique_languages":4,"has_readme_projects":True,"longest_streak_days":16,"days_since_last_commit":9,"github_score":61.7},
     "cp":{"lc_solved_easy":65,"lc_solved_medium":88,"lc_solved_hard":12,"lc_contest_rating":1620.0,"lc_contests_attended":12,"lc_avg_attempts_per_problem":1.9,"cf_rating":1280,"cf_max_rating":1340,"cf_contests_attended":10,"cf_problems_solved":160,"cc_rating":1500,"cc_problems_solved":75,"authenticity_score":0.94,"flag_suspicious":False,"flag_reason":"no issues detected","cp_score":56.8},
     "res":{"raw_skills":"JavaScript TypeScript React Next.js Node.js Express MongoDB GraphQL Tailwind CSS","raw_projects":"Full-stack SaaS project management. Chrome extension 500 users. GraphQL API e-commerce.","raw_internships":"Frontend Developer Intern Razorpay June 2023.","raw_experience":"Freelance full-stack developer 6 months 4 clients.","raw_certifications":"Meta Frontend Developer Certificate. MongoDB Associate Developer.","raw_education":"B.Tech IT CGPA 8.4. 12th 81%. 10th 86%."}},
]

DRIVES = [
    {"company_name":"Google","role_title":"Software Engineering Intern",
     "jd_text":"Looking for Software Engineering Interns with strong data structures algorithms system design. Experience with competitive programming Python Java C++. Distributed systems machine learning open source contributions preferred. Active GitHub required.",
     "shortlist_count":5,"weight_skills":0.28,"weight_projects":0.20,"weight_experience":0.15,"weight_github":0.15,"weight_cp":0.17,"weight_cgpa":0.05,
     "boost_startup_founder":1.10,"boost_ml_internship":1.05,"boost_open_source":1.15,
     "min_cgpa":7.5,"max_backlogs":0,"allowed_branches":json.dumps(["CSE","IT","AIML","AIDS"])},

    {"company_name":"TCS","role_title":"Systems Engineer",
     "jd_text":"TCS hiring Systems Engineers for digital transformation. Knowledge of Java Python C# databases SQL communication skills required. CGPA above 6.0 no active backlogs. All branches eligible. Cloud database certifications preferred.",
     "shortlist_count":8,"weight_skills":0.30,"weight_projects":0.20,"weight_experience":0.18,"weight_github":0.10,"weight_cp":0.07,"weight_cgpa":0.15,
     "boost_startup_founder":1.0,"boost_ml_internship":1.0,"boost_open_source":1.0,
     "min_cgpa":6.0,"max_backlogs":0,"allowed_branches":json.dumps([])},
]


def seed():
    with app.app_context():
        print("\nClearing old sample data...")
        DriveScore.query.delete()
        Drive.query.delete()
        CPSignal.query.delete()
        GitHubSignal.query.delete()
        Resume.query.delete()
        for prefix in ["CS2021","IT2021","ECE2021","AIDS2021","AIML2021"]:
            Student.query.filter(Student.erp_id.like(f"{prefix}%")).delete()
        db.session.commit()

        print("Creating 10 students...")
        for s in STUDENTS:
            st = Student(
                erp_id=s["erp_id"], name=s["name"], email=s["email"],
                branch=s["branch"], year=s["year"], cgpa=s["cgpa"],
                backlogs=s.get("backlogs",0),
                tenth_pct=s.get("tenth_pct"), twelfth_pct=s.get("twelfth_pct"),
                github_url=s.get("github_url",""),
                leetcode_user=s.get("leetcode_user",""),
                codeforces_user=s.get("codeforces_user",""),
                is_startup_founder=s.get("is_startup_founder",False),
                has_ml_internship=s.get("has_ml_internship",False),
                has_open_source=s.get("has_open_source",False),
            )
            db.session.add(st)
            db.session.flush()

            g = s["gh"]
            db.session.add(GitHubSignal(student_id=st.id,
                total_repos=g["total_repos"], total_commits_90d=g["total_commits_90d"],
                unique_languages=g["unique_languages"], has_readme_projects=g["has_readme_projects"],
                longest_streak_days=g["longest_streak_days"], days_since_last_commit=g["days_since_last_commit"],
                github_score=g["github_score"], fetched_at=datetime.utcnow()))

            c = s["cp"]
            db.session.add(CPSignal(student_id=st.id,
                lc_solved_easy=c["lc_solved_easy"], lc_solved_medium=c["lc_solved_medium"],
                lc_solved_hard=c["lc_solved_hard"], lc_contest_rating=c["lc_contest_rating"],
                lc_contests_attended=c["lc_contests_attended"],
                lc_avg_attempts_per_problem=c["lc_avg_attempts_per_problem"],
                cf_rating=c["cf_rating"], cf_max_rating=c["cf_max_rating"],
                cf_contests_attended=c["cf_contests_attended"], cf_problems_solved=c["cf_problems_solved"],
                cc_rating=c["cc_rating"], cc_problems_solved=c["cc_problems_solved"],
                authenticity_score=c["authenticity_score"], flag_suspicious=c["flag_suspicious"],
                flag_reason=c["flag_reason"], cp_score=c["cp_score"],
                fetched_at=datetime.utcnow()))

            r = s["res"]
            db.session.add(Resume(student_id=st.id,
                raw_skills=r["raw_skills"], raw_projects=r["raw_projects"],
                raw_internships=r.get("raw_internships",""),
                raw_experience=r.get("raw_experience",""),
                raw_certifications=r.get("raw_certifications",""),
                raw_education=r.get("raw_education",""),
                raw_full=" ".join(v for v in r.values() if v),
                parsed_at=datetime.utcnow()))

            print(f"  + {st.name} ({st.branch}) CGPA {st.cgpa}")

        db.session.commit()

        print("\nCreating drives and running scoring...")
        print("(SBERT loads on first run — wait ~30 seconds)\n")
        for d in DRIVES:
            drive = Drive(
                company_name=d["company_name"], role_title=d["role_title"],
                jd_text=d["jd_text"], shortlist_count=d["shortlist_count"],
                weight_skills=d["weight_skills"], weight_projects=d["weight_projects"],
                weight_experience=d["weight_experience"], weight_github=d["weight_github"],
                weight_cp=d["weight_cp"], weight_cgpa=d["weight_cgpa"],
                boost_startup_founder=d["boost_startup_founder"],
                boost_ml_internship=d["boost_ml_internship"],
                boost_open_source=d["boost_open_source"],
                min_cgpa=d["min_cgpa"], max_backlogs=d["max_backlogs"],
                allowed_branches=d["allowed_branches"],
            )
            db.session.add(drive)
            db.session.flush()

            from app.services.scoring_engine import run_drive_scoring
            result = run_drive_scoring(drive.id, db.session)
            print(f"  + {drive.company_name}: scored={result['scored']} excluded={result['excluded']} errors={result['errors']}")

        db.session.commit()
        print("\n" + "="*45)
        print("Done! Open http://localhost:5000")
        print("Email:    admin@placement.com")
        print("Password: admin123")
        print("="*45)

if __name__ == "__main__":
    seed()
