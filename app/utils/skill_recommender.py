import numpy as np
from collections import Counter


def log_likelihood(user_skills, job_skills):
    """
    Menghitung log likelihood dari skill pengguna
    dibandingkan dengan skill pekerjaan.

    Parameters:
    - user_skills: Set atau list berisi skill yang dimiliki oleh pengguna.
    - job_skills: Set atau list berisi skill yang diperlukan untuk pekerjaan.

    Returns:
    - log_likelihood_value: Nilai log likelihood untuk rekomendasi skill.
    """
    user_skills_set = set(user_skills)
    job_skills_set = set(job_skills)

    # Menghindari pembagian dengan nol
    if len(job_skills_set) == 0:
        # Log likelihood tak terdefinisi
        # jika tidak ada skill pekerjaan
        return -np.inf

    # Menghitung skill yang dimiliki pengguna yang sesuai dengan pekerjaan
    matching_skills = user_skills_set.intersection(job_skills_set)
    matching_skill_count = len(matching_skills)

    # Menghitung probabilitas
    probability = matching_skill_count / len(job_skills_set)

    # Menghitung log likelihood
    log_likelihood_value = np.log(probability) if probability > 0 else -np.inf

    return log_likelihood_value


def recommend_skills(user_skills, job_skills):
    """
    Merekomendasikan skill yang perlu dipelajari
    berdasarkan skill yang diperlukan di lowongan pekerjaan.

    Parameters:
    - user_skills: List berisi skill yang dimiliki oleh pengguna.
    - job_skills: Set atau list berisi skill yang diperlukan untuk pekerjaan.

    Returns:
    - recommended_skills: List skill yang direkomendasikan untuk dipelajari.
    """
    # Menghitung frekuensi skill yang diperlukan
    skill_counts = Counter(job_skills)

    # Mengumpulkan skill yang tidak dimiliki pengguna
    user_skill_set = set(user_skills)
    recommended_skills = [
        skill for skill in skill_counts if skill not in user_skill_set
    ]

    # Mengurutkan skill berdasarkan frekuensi (berdasarkan seberapa banyak mereka muncul)
    recommended_skills.sort(key=lambda skill: skill_counts[skill], reverse=True)

    return recommended_skills


JOB_TITLE_VARIATIONS = {
    "Backend Engineer/Developer": [
        "Backend",
        "Back End",
        "Backend Engineer",
        "Back End Engineer",
        "Backend Developer",
        "Back End Developer",
        "Backend Software Engineer",
        "Back End Software Engineer",
        "Backend Software Developer",
        "Back End Software Developer"
    ],
    "Frontend Engineer/Developer": [
        "Frontend Engineer",
        "Front End Engineer",
        "Frontend Developer",
        "Front End Developer",
        "Frontend Software Engineer",
        "Front End Software Engineer",
        "Frontend Software Developer",
        "Front End Software Developer"
    ],
    "Fullstack Engineer/Developer": [
        "Fullstack Engineer",
        "Full Stack Engineer",
        "Fullstack Developer",
        "Full Stack Developer",
        "Fullstack Software Engineer",
        "Full Stack Software Engineer",
        "Fullstack Software Developer",
        "Full Stack Software Developer"
    ],
    "Devops": [
        "DevOps Engineer",
        "DevOps Developer",
        "DevOps Specialist",
        "DevOps Consultant",
        "DevOps Architect"
    ],
    "QA/Quality Assurance Engineer": [
        "QA Engineer",
        "Quality Assurance Engineer",
        "QA Developer",
        "Quality Assurance Developer",
        "QA Tester",
        "Quality Assurance Tester",
        "QA Analyst",
        "Quality Assurance Analyst"
    ],
    "Cloud Engineer": [
        "Cloud Engineer",
        "Cloud Developer",
        "Cloud Architect",
        "Cloud Solutions Engineer",
        "Cloud Infrastructure Engineer",
        "AWS Engineer",
        "Azure Engineer",
        "GCP Engineer"
    ],
    "Business Analyst": [
        "Business Analyst",
        "Business Systems Analyst",
        "IT Business Analyst",
        "Technical Business Analyst",
        "Senior Business Analyst",
        "Lead Business Analyst"
    ]
}



# # Data Pengguna dan Lowongan Pekerjaan
# user_name = "Maman"
# user_skills = ['Python', 'Java', 'JavaScript', 'Docker', 'PostgreSQL']

# job_postings = [
#     {"title": "Backend Engineer", "skills": ['Python', 'Kubernetes', 'AWS']},
#     {"title": "Backend Developer", "skills": ['ExpressJS', 'JavaScript', 'Prisma', 'AWS']},
#     {"title": "Backend Developer", "skills": ['Laravel', 'MySQL']}
# ]

# # Menghitung log likelihood untuk setiap lowongan pekerjaan dan memilih yang terbaik
# max_ll_value = -np.inf
# best_job = None

# for job in job_postings:
#     title = job["title"]
#     job_skills = job["skills"]
#     ll_value = log_likelihood(user_skills, job_skills)

#     if ll_value > max_ll_value:
#         max_ll_value = ll_value
#         best_job = job

# # Menampilkan informasi tentang lowongan terbaik
# if best_job is not None:
#     title = best_job["title"]
#     job_skills = best_job["skills"]
#     print(f'Lowongan terbaik: {title}')
#     print(f'Skill pekerjaan: {job_skills}')
#     print(f'Log Likelihood tertinggi: {max_ll_value:.4f}')

#     # Merekomendasikan skill yang perlu dipelajari berdasarkan lowongan terbaik
#     recommended_skills = recommend_skills(user_skills, job_skills)
#     print("\nSkill yang direkomendasikan untuk dipelajari:")
#     print(recommended_skills)
# else:
#     print("Tidak ada lowongan pekerjaan yang tersedia.")



