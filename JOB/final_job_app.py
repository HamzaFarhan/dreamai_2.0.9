import json
from uuid import uuid4
import streamlit as st
from job_code import (
    JOBS_COLLECTION_NAME,
    JOBS_DIR,
    PROFILES_COLLECTION_NAME,
    PROFILES_DIR,
    JobPost,
    UserProfile,
    create_job_post,
    create_models_and_collection,
    create_reasoning,
    create_user_profile,
    extract_text,
)

from dreamai.chroma import chroma_collection

N_RESULTS = 2


def display_user_profile(
    user_profile: UserProfile | None, reasoning: str | None = None
):
    if user_profile is not None:
        user_dfs = user_profile.create_dfs()
        st.header(f":blue[{user_profile.name}]", divider=True)
        st.subheader(f":green[{user_profile.title}]")
        st.write(user_profile.email)
        if user_profile.years_of_experience:
            st.write(f"Years of Experience: :blue[{user_profile.years_of_experience}]")
        if reasoning:
            with st.expander(":rainbow[Reasoning] 🧠"):
                st.write(reasoning)
        with st.expander("Summary 📝"):
            st.write(user_profile.summary)
        if user_profile.experiences:
            with st.expander("Experiences 🏢"):
                st.dataframe(user_dfs["experiences"])
        if user_profile.skills:
            with st.expander("Skills 🛠️"):
                st.dataframe(user_dfs["skills"])
        if user_profile.certifications:
            with st.expander("Certifications 📜"):
                st.dataframe(user_dfs["certifications"])
        if user_profile.education:
            with st.expander("Education 🎓"):
                st.dataframe(user_dfs["education"])
        if user_profile.interested_job_titles:
            with st.expander("Interested Job Titles 🕴️"):
                for title in user_profile.interested_job_titles:
                    st.write(title)


def display_job_post(job_post: JobPost | None, reasoning: str | None = None):
    if job_post is not None:
        job_dfs = job_post.create_dfs()
        st.header(f":red[{job_post.job_description.title}]", divider=True)
        if job_post.job_description.company:
            st.subheader(f":orange[{job_post.job_description.company}]")
        st.write(
            f"Minimum Years of Experience: :orange[{job_post.years_of_experience}]"
        )
        if reasoning:
            with st.expander(":rainbow[Reasoning] 🧠"):
                st.write(reasoning)
        # st.write(f"Minimum Education Level: :orange[{job_post.min_education}]")
        with st.expander("Job Description 📝"):
            st.write(job_post.job_description.description)
        if job_post.skills:
            with st.expander("Required Skills 🛠️"):
                st.dataframe(job_dfs["skills"])
        if job_post.education:
            with st.expander("Required Education 🎓"):
                st.dataframe(job_dfs["education"])


def filter_profiles(
    job_post: JobPost, top_profiles: dict[str, UserProfile]
) -> dict[str, UserProfile]:
    filters = st.popover(":rainbow[Filters]")
    years_of_experience = filters.checkbox(
        "Years of Experience", True, key="profiles_years"
    )
    filtered_profiles = {}
    for profile_id, profile in top_profiles.items():
        if (
            years_of_experience
            and profile.years_of_experience < job_post.years_of_experience
        ):
            continue
        filtered_profiles[profile_id] = profile
    return filtered_profiles


def filter_jobs(
    user_profile: UserProfile, top_jobs: dict[str, JobPost]
) -> dict[str, JobPost]:
    filters = st.popover(":rainbow[Filters]")
    years_of_experience = filters.checkbox(
        "Years of Experience", True, key="jobs_years"
    )
    # min_education = filters.checkbox("Minimum Education", True, key="jobs_education")
    filtered_jobs = {}
    for job_id, job in top_jobs.items():
        if (
            years_of_experience
            and user_profile.years_of_experience < job.years_of_experience
        ):
            continue
        # if min_education and user_profile.max_education < job.min_education:
        #     continue
        filtered_jobs[job_id] = job
    return filtered_jobs


def load_txt_file(file_data):
    if not file_data:
        return file_data
    if file_data.type == "text/plain":
        return file_data.read().decode("utf-8")
    return file_data


@st.cache_resource
def load_collection(collection_name: str):
    return chroma_collection(collection_name)


st.set_page_config(page_title="🧾🤝")
st.title("🧾🤝")

profiles_collection = load_collection(PROFILES_COLLECTION_NAME)
jobs_collection = load_collection(JOBS_COLLECTION_NAME)
tab1, tab2 = st.tabs([":orange[Find Candidates]", ":green[Find Jobs]"])
with tab1:
    st.title(":orange[Find Candidates]")
    resume_files = st.file_uploader(
        "Upload resume(s)", type=["pdf"], accept_multiple_files=True
    )
    process_files = st.button("Process Resumes 🧾")
    if resume_files and process_files:
        with st.spinner("Collecting resumes...⏳"):
            create_models_and_collection(
                data=resume_files,
                creator_fn=create_user_profile,
                models_dir=PROFILES_DIR,
                collection=profiles_collection,
            )
    job_description = st.text_area("Enter the job description", height=180)
    job_file = st.file_uploader("Or upload a job description", type=["pdf", "txt"])
    job_description = job_description or ""
    if job_file:
        if job_file.type == "text/plain":
            job_description += job_file.read().decode("utf-8")
        else:
            job_description += extract_text(job_file)
    print(f"\n\nJOB DESCRIPTION\n{job_description}\n\n")
    st.session_state["n_results"] = st.number_input(
        "Number of Candidates",
        value=min(N_RESULTS, profiles_collection.count()),
        min_value=min(1, profiles_collection.count()),
        max_value=profiles_collection.count(),
    )
    find_candidates = st.button("Find Candidates 🎯", type="primary")
    if job_description and find_candidates:
        if profiles_collection.count() == 0:
            st.error("No user profiles found. Please upload some resumes 👀")
        else:
            st.session_state["top_profile_docs"] = None
            with st.spinner("Finding candidates...🔍"):
                job_post_ = create_job_post(job_description)
                if job_post_ is not None:
                    create_models_and_collection(
                        data=[job_post_],
                        creator_fn=create_job_post,
                        models_dir=JOBS_DIR,
                        collection=jobs_collection,
                    )
                    st.session_state["job_post"] = job_post_
                    st.session_state["job_post_id"] = f"job_{uuid4()}"
    if st.session_state.get("job_post", None) is not None:
        n_results = st.session_state.get("n_results", N_RESULTS)
        job_post: JobPost = st.session_state["job_post"]
        display_job_post(job_post)
        top_profile_docs = st.session_state.get("top_profile_docs", None)
        if top_profile_docs is None:
            top_profile_docs = profiles_collection.query(
                query_texts=str(job_post), n_results=n_results
            )
            st.session_state["top_profile_docs"] = top_profile_docs
        top_profiles = {
            id: UserProfile(**json.load(open(PROFILES_DIR / f"{id}.json", "r")))
            for id in top_profile_docs["ids"][0]
        }
        for profile_id, top_profile in top_profiles.items():
            reasoning_dict = st.session_state.get("reasoning_dict", {})
            reasoning_id = f"{st.session_state['job_post_id']}_{profile_id}"
            if reasoning_dict.get(reasoning_id, None) is None:
                reasoning_dict[reasoning_id] = create_reasoning(
                    user_profile=top_profile, job_post=job_post
                )
            st.session_state["reasoning_dict"] = reasoning_dict

        filtered_profiles = filter_profiles(
            job_post=job_post, top_profiles=top_profiles
        )
        if len(filtered_profiles) == 0:
            st.error("No candidates found with the given job description + filters 🤷‍♂️")
        else:
            st.header(
                f":green[Top :orange[{len(filtered_profiles)}] Candidate(s) 🏆]",
                divider=True,
            )
            for i, (profile_id, profile) in enumerate(
                filtered_profiles.items(), start=1
            ):
                button_name = f":yellow[Candidate {i}]"
                # if i == 1:
                #     button_name += " 🥇"
                # if i == 2:
                #     button_name += " 🥈"
                # if i == 3:
                #     button_name += " 🥉"
                reasoning_id = f"{st.session_state['job_post_id']}_{profile_id}"
                reasoning = st.session_state.get("reasoning_dict", {}).get(
                    reasoning_id, None
                )
                if st.button(button_name):
                    display_user_profile(user_profile=profile, reasoning=reasoning)

with tab2:
    st.title(":green[Find Jobs]")
    job_files = st.file_uploader(
        "Upload job descriptions", type=["pdf", "txt"], accept_multiple_files=True
    )
    process_files = st.button("Process Job Descriptions 🧾")
    if job_files and process_files:
        with st.spinner("Collecting job descriptions...⏳"):
            for i, job_file in enumerate(job_files):
                if job_file.type == "text/plain":
                    job_description = job_file.read().decode("utf-8")
                else:
                    job_description = extract_text(job_file)
                create_models_and_collection(
                    data=[job_description],
                    creator_fn=create_job_post,
                    models_dir=JOBS_DIR,
                    collection=jobs_collection,
                )
    info = st.text_area("Information about the candidate", height=180)
    resume_file = st.file_uploader("Upload a resume for better results", type=["pdf"])
    st.session_state["n_results"] = st.number_input(
        "Number of Jobs",
        value=min(N_RESULTS, jobs_collection.count()),
        min_value=min(1, jobs_collection.count()),
        max_value=jobs_collection.count(),
    )
    find_jobs = st.button("Find Jobs 🎯", type="primary")
    if (resume_file or info) and find_jobs:
        if jobs_collection.count() == 0:
            st.error("No job posts found. Please upload some job descriptions 👀")
        else:
            st.session_state["top_job_docs"] = None
            with st.spinner("Finding jobs...🔍"):
                resume_text = ""
                if resume_file:
                    resume_text = extract_text(resume_file)
                if info:
                    resume_text += f"\n<info>\n{info.strip()}\n</info>"
                user_profile_ = create_user_profile(data=resume_text.strip())
                print(f"\n\nUSER PROFILE\n{user_profile_}\n\n")
                if user_profile_ is not None:
                    st.session_state["user_profile"] = user_profile_
                    st.session_state["user_profile_id"] = f"user_{uuid4()}"
                    create_models_and_collection(
                        data=[user_profile_],
                        creator_fn=create_user_profile,
                        models_dir=PROFILES_DIR,
                        collection=profiles_collection,
                    )
    if st.session_state.get("user_profile", None) is not None:
        n_results = st.session_state.get("n_results", N_RESULTS)
        user_profile: UserProfile = st.session_state["user_profile"]
        display_user_profile(user_profile)
        top_job_docs = st.session_state.get("top_job_docs", None)
        if top_job_docs is None:
            top_job_docs = jobs_collection.query(
                query_texts=str(user_profile), n_results=n_results
            )
            st.session_state["top_job_docs"] = top_job_docs
        top_jobs = {
            id: JobPost(**json.load(open(JOBS_DIR / f"{id}.json", "r")))
            for id in top_job_docs["ids"][0]
        }
        for job_id, top_job in top_jobs.items():
            reasoning_dict = st.session_state.get("reasoning_dict", {})
            reasoning_id = f"{st.session_state['user_profile_id']}_{job_id}"
            if reasoning_dict.get(reasoning_id, None) is None:
                reasoning_dict[reasoning_id] = create_reasoning(
                    user_profile=user_profile, job_post=top_job
                )
            st.session_state["reasoning_dict"] = reasoning_dict
        filtered_jobs = filter_jobs(user_profile=user_profile, top_jobs=top_jobs)
        if len(filtered_jobs) == 0:
            st.error("No jobs found for the given resume + filters 🤷‍♂️")
        else:
            st.header(
                f":orange[Top :green[{len(filtered_jobs)}] Job(s) 🏆]", divider=True
            )
            for i, (job_id, job) in enumerate(filtered_jobs.items(), start=1):
                button_name = f":yellow[Job {i}]"
                # if i == 1:
                #     button_name += " 🥇"
                # if i == 2:
                #     button_name += " 🥈"
                # if i == 3:
                #     button_name += " 🥉"
                reasoning_id = f"{st.session_state['user_profile_id']}_{job_id}"
                reasoning = st.session_state.get("reasoning_dict", {}).get(
                    reasoning_id, None
                )
                if st.button(button_name):
                    display_job_post(job_post=job, reasoning=reasoning)
