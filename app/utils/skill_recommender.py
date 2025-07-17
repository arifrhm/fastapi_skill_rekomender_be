import numpy as np
from collections import Counter


def cosine_similarity(set_a, set_b, universe):
    """
    Calculate cosine similarity using a fixed skill universe.
    """
    a = set(set_a)
    b = set(set_b)

    vec_a = np.array([1 if skill in a else 0 for skill in universe])
    vec_b = np.array([1 if skill in b else 0 for skill in universe])

    dot_product = np.dot(vec_a, vec_b)
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)


def entropy(*counts):
    """
    Calculate entropy for LLS similarity calculation.
    """
    N = sum(counts)
    H = 0.0
    for k in counts:
        if k > 0:
            H += k * np.log(k / N)
    return H


def llr_similarity(set_a, set_b, universe=None):
    """
    Calculate Log Likelihood Ratio similarity between two sets of skills.

    Parameters:
    - set_a: First set of skills (e.g., user skills)
    - set_b: Second set of skills (e.g., job skills)
    - universe: Optional universe set containing all possible skills

    Returns:
    - llr: Log Likelihood Ratio similarity score
    """
    set_a = set(set_a)
    set_b = set(set_b)
    if universe is None:
        universe = set_a | set_b
    else:
        universe = set(universe)

    k11 = len(set_a & set_b)
    k12 = len(set_b - set_a)
    k21 = len(set_a - set_b)
    k22 = len(universe - (set_a | set_b))
    # N = k11 + k12 + k21 + k22

    H_k = entropy(k11, k12, k21, k22)
    H_ki = entropy(k11 + k12, k21 + k22)
    H_kj = entropy(k11 + k21, k12 + k22)

    llr = 2 * (H_k - H_ki - H_kj)
    return llr


def recommend_skills(user_skills, job_skills):
    """
    Recommend skills that need to be learned based on job requirements.

    Parameters:
    - user_skills: List of skills possessed by the user
    - job_skills: List of skills required for the job

    Returns:
    - recommended_skills: List of recommended skills to learn
    """
    skill_counts = Counter(job_skills)
    user_skill_set = set(user_skills)
    recommended_skills = [
        skill for skill in skill_counts if skill not in user_skill_set
    ]
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
        "Back End Software Developer",
    ],
    "Frontend Engineer/Developer": [
        "Frontend",
        "Front End",
        "Frontend Engineer",
        "Front End Engineer",
        "Frontend Developer",
        "Front End Developer",
        "Frontend Software Engineer",
        "Front End Software Engineer",
        "Frontend Software Developer",
        "Front End Software Developer",
    ],
    "Fullstack Engineer/Developer": [
        "Fullstack",
        "Full Stack",
        "Fullstack Engineer",
        "Full Stack Engineer",
        "Fullstack Developer",
        "Full Stack Developer",
        "Fullstack Software Engineer",
        "Full Stack Software Engineer",
        "Fullstack Software Developer",
        "Full Stack Software Developer",
    ],
    "Devops": [
        "Devops",
        "DevOps",
        "DevOps Engineer",
        "DevOps Developer",
        "DevOps Specialist",
        "DevOps Consultant",
        "DevOps Architect",
    ],
    "QA/Quality Assurance Engineer": [
        "QA",
        "Quality Assurance",
        "QA Engineer",
        "Quality Assurance Engineer",
        "QA Developer",
        "Quality Assurance Developer",
        "QA Tester",
        "Quality Assurance Tester",
        "QA Analyst",
        "Quality Assurance Analyst",
    ],
    "Cloud Engineer": [
        "Cloud Engineer",
        "Cloud Developer",
        "Cloud Architect",
        "Cloud Solutions Engineer",
        "Cloud Infrastructure Engineer",
        "AWS Engineer",
        "Azure Engineer",
        "GCP Engineer",
    ],
    "Business Analyst": [
        "BA",
        "Business",
        "Business Analyst",
        "Business Systems Analyst",
        "IT Business Analyst",
        "Technical Business Analyst",
        "Senior Business Analyst",
        "Lead Business Analyst",
    ],
}
