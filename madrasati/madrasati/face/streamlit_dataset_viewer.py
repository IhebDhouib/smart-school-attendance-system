"""
Streamlit Dataset Viewer for Face Recognition System
Displays all faces in dataset folder and their corresponding encodings
WITH DELETE AND ENCODE FUNCTIONALITY
"""

import streamlit as st
import cv2
import pickle
import os
import numpy as np
from pathlib import Path
import pandas as pd
from PIL import Image
import shutil
import requests
from datetime import datetime

# Configuration
DATASET_DIR = os.getenv("DATASET_DIR", "dataset")
ENCODINGS_FILE = os.getenv("ENCODINGS_FILE_ARCFACE", "encodings_arcface.pkl")
FACE_API_URL = os.getenv("FACE_API_URL", "http://localhost:8000")

# Log file paths
FACE_API_LOG = os.getenv('FACE_API_LOG_FILE', 'face_api_logs.log')
FACE_RECOGNITION_LOG = os.getenv('FACE_RECOGNITION_LOG_FILE', 'face_recognition_app.log')
ATTENDANCE_CSV = os.path.join(os.getenv("LOG_DIR", "logs"), "logs.csv")

st.set_page_config(
    page_title="Face Dataset Manager",
    page_icon="👤",
    layout="wide"
)

def load_encodings():
    """Load encodings from pickle file"""
    try:
        with open(ENCODINGS_FILE, "rb") as f:
            data = pickle.load(f)
            embeddings = data.get("embeddings", [])
            names = data.get("names", [])
            return embeddings, names
    except FileNotFoundError:
        st.error(f"❌ Encodings file not found: {ENCODINGS_FILE}")
        return [], []
    except Exception as e:
        st.error(f"❌ Error loading encodings: {e}")
        return [], []

def save_encodings(embeddings, names):
    """Save encodings to pickle file"""
    try:
        # Backup existing file
        if os.path.exists(ENCODINGS_FILE):
            backup_file = f"{ENCODINGS_FILE}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(ENCODINGS_FILE, backup_file)
            st.success(f"✅ Created backup: {backup_file}")
        
        # Save new encodings
        data = {"embeddings": embeddings, "names": names}
        with open(ENCODINGS_FILE, "wb") as f:
            pickle.dump(data, f)
        return True
    except Exception as e:
        st.error(f"❌ Error saving encodings: {e}")
        return False

def get_dataset_images():
    """Get all images from dataset directory"""
    images_dict = {}
    
    if not os.path.exists(DATASET_DIR):
        st.warning(f"⚠️  Dataset directory not found: {DATASET_DIR}")
        return images_dict
    
    # Iterate through student folders
    for student_folder in os.listdir(DATASET_DIR):
        student_path = os.path.join(DATASET_DIR, student_folder)
        
        if os.path.isdir(student_path):
            images = []
            for img_file in os.listdir(student_path):
                if img_file.lower().endswith(('.jpg', '.jpeg', '.png')):
                    img_path = os.path.join(student_path, img_file)
                    images.append(img_path)
            
            if images:
                images_dict[student_folder] = sorted(images)
    
    return images_dict

def delete_image(img_path):
    """Delete an image file with retry logic"""
    import time
    import gc
    
    max_retries = 3
    retry_delay = 0.5
    
    for attempt in range(max_retries):
        try:
            # Force garbage collection to close any file handles
            gc.collect()
            
            # Check if file exists
            if not os.path.exists(img_path):
                st.warning(f"⚠️ File not found: {os.path.basename(img_path)}")
                return False
            
            # Try to delete
            os.remove(img_path)
            st.success(f"✅ Deleted: {os.path.basename(img_path)}")
            return True
            
        except PermissionError as e:
            if attempt < max_retries - 1:
                st.warning(f"⚠️ File in use, retrying... (attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
            else:
                st.error(f"❌ Permission denied after {max_retries} attempts.")
                st.info("💡 The file is locked by another process. Try:")
                st.info("   1. Close any image preview windows")
                st.info("   2. Wait a few seconds")
                st.info("   3. Check if another application is using the file")
                return False
        except Exception as e:
            st.error(f"❌ Error deleting image: {e}")
            return False
    
    return False

def delete_student_folder(student_id):
    """Delete entire student folder"""
    try:
        folder_path = os.path.join(DATASET_DIR, student_id)
        shutil.rmtree(folder_path)
        st.success(f"✅ Deleted folder for student: {student_id}")
        return True
    except Exception as e:
        st.error(f"❌ Error deleting folder: {e}")
        return False

def delete_student_encodings(student_id):
    """Delete all encodings for a student"""
    try:
        embeddings, names = load_encodings()
        
        # Filter out the student's encodings
        new_embeddings = [emb for emb, name in zip(embeddings, names) if name != student_id]
        new_names = [name for name in names if name != student_id]
        
        removed_count = len(embeddings) - len(new_embeddings)
        
        if removed_count > 0:
            if save_encodings(new_embeddings, new_names):
                st.success(f"✅ Deleted {removed_count} encoding(s) for student: {student_id}")
                return True
        else:
            st.warning(f"⚠️  No encodings found for student: {student_id}")
            return False
    except Exception as e:
        st.error(f"❌ Error deleting encodings: {e}")
        return False

def encode_student_images(student_id):
    """Call Face API to encode student images"""
    try:
        response = requests.post(
            f"{FACE_API_URL}/students/encodings",
            json={"student_id": student_id},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            st.success(f"✅ Encoded {result.get('images_processed', 0)} image(s) for student: {student_id}")
            return True
        else:
            st.error(f"❌ Encoding failed: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to Face API. Make sure the service is running.")
        return False
    except Exception as e:
        st.error(f"❌ Error encoding images: {e}")
        return False

def encode_all_students():
    """Encode all students in dataset"""
    try:
        response = requests.post(
            f"{FACE_API_URL}/students/encodings/rebuild",
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            st.success(f"✅ Rebuilt encodings: {result.get('total_encodings', 0)} total encoding(s)")
            return True
        else:
            st.error(f"❌ Rebuild failed: {response.text}")
            return False
    except Exception as e:
        st.error(f"❌ Error rebuilding encodings: {e}")
        return False

def read_log_file(log_path, num_lines=100):
    """Read last N lines from log file"""
    try:
        if not os.path.exists(log_path):
            return []
        
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            return lines[-num_lines:] if len(lines) > num_lines else lines
    except Exception as e:
        return [f"Error reading log: {e}"]

def parse_log_line(line):
    """Parse log line into timestamp, level, and message"""
    try:
        # Format: 2026-01-13 10:30:15 - INFO - Message
        parts = line.split(' - ', 2)
        if len(parts) >= 3:
            return {
                'timestamp': parts[0].strip(),
                'level': parts[1].strip(),
                'message': parts[2].strip()
            }
        return {'timestamp': '', 'level': 'UNKNOWN', 'message': line.strip()}
    except:
        return {'timestamp': '', 'level': 'UNKNOWN', 'message': line.strip()}

def read_attendance_csv(csv_path, num_lines=100):
    """Read attendance CSV file"""
    try:
        if not os.path.exists(csv_path):
            return pd.DataFrame()
        
        df = pd.read_csv(csv_path, names=['Timestamp', 'Student ID', 'Camera Type', 'Confidence'])
        return df.tail(num_lines)
    except Exception as e:
        st.error(f"Error reading attendance CSV: {e}")
        return pd.DataFrame()

def filter_logs_by_level(logs, level_filter):
    """Filter logs by level"""
    if level_filter == "All":
        return logs
    return [log for log in logs if level_filter.upper() in log.upper()]

def filter_logs_by_search(logs, search_query):
    """Filter logs by search query"""
    if not search_query:
        return logs
    return [log for log in logs if search_query.lower() in log.lower()]

def main():
    st.title("👤 Face Dataset Manager")
    st.markdown("---")
    
    # Sidebar
    st.sidebar.title("📊 Statistics")
    
    # Load data
    embeddings, names = load_encodings()
    dataset_images = get_dataset_images()
    
    # Display statistics
    st.sidebar.metric("Total Encodings", len(embeddings))
    st.sidebar.metric("Unique Students (Encodings)", len(set(names)))
    st.sidebar.metric("Students in Dataset", len(dataset_images))
    st.sidebar.metric("Total Images", sum(len(imgs) for imgs in dataset_images.values()))
    
    # Encoding dimension
    if embeddings:
        st.sidebar.metric("Embedding Dimension", len(embeddings[0]))
    
    st.sidebar.markdown("---")
    
    # Bulk actions in sidebar
    st.sidebar.subheader("🔧 Bulk Actions")
    
    if st.sidebar.button("🔄 Rebuild All Encodings", type="primary"):
        with st.spinner("Encoding all students..."):
            if encode_all_students():
                st.rerun()
    
    if st.sidebar.button("🔄 Refresh Data"):
        st.rerun()
    
    # Main content tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📸 Dataset Images", "🧠 Encodings", "🔍 Compare", "📊 Analysis", "📝 Logs"])
    
    # Tab 1: Dataset Images with DELETE and ENCODE buttons
    with tab1:
        st.header("📸 Dataset Images")
        
        if not dataset_images:
            st.warning("⚠️  No images found in dataset directory")
        else:
            # Search/filter
            search_query = st.text_input("🔍 Search by Student ID", "")
            
            # Filter students
            filtered_students = {
                student_id: images 
                for student_id, images in dataset_images.items()
                if search_query.lower() in student_id.lower()
            }
            
            st.write(f"Showing {len(filtered_students)} student(s)")
            
            # Display images in grid with actions
            for student_id, images in sorted(filtered_students.items()):
                with st.expander(f"👤 Student: {student_id} ({len(images)} photo(s))", expanded=True):
                    # Student-level actions
                    col_action1, col_action2, col_action3 = st.columns([1, 1, 4])
                    
                    with col_action1:
                        if st.button(f"🔄 Encode {student_id}", key=f"encode_{student_id}"):
                            with st.spinner(f"Encoding {student_id}..."):
                                if encode_student_images(student_id):
                                    st.rerun()
                    
                    with col_action2:
                        if st.button(f"🗑️ Delete All", key=f"delete_all_{student_id}", type="secondary"):
                            if st.session_state.get(f"confirm_delete_{student_id}"):
                                if delete_student_folder(student_id):
                                    if delete_student_encodings(student_id):
                                        st.rerun()
                            else:
                                st.session_state[f"confirm_delete_{student_id}"] = True
                                st.warning("⚠️ Click again to confirm deletion")
                    
                    st.markdown("---")
                    
                    # Display images in grid
                    cols = st.columns(min(4, len(images)))
                    
                    for idx, img_path in enumerate(images):
                        with cols[idx % 4]:
                            try:
                                # Load image and close file handle immediately
                                with Image.open(img_path) as img:
                                    img_copy = img.copy()  # Create a copy to close the file
                
                                    st.image(img_copy, caption=os.path.basename(img_path), use_container_width=True)
                
                                    # Delete button for individual image
                                    if st.button(f"🗑️ Delete", key=f"delete_{img_path}"):
                                        if delete_image(img_path):
                                            st.rerun()
                            except Exception as e:
                                st.error(f"Error loading {img_path}: {e}")
    
    # Tab 2: Encodings with DELETE buttons
    with tab2:
        st.header("🧠 Face Encodings")
        
        if not embeddings:
            st.warning("⚠️  No encodings found")
        else:
            # Group encodings by student
            encoding_counts = {}
            for name in names:
                encoding_counts[name] = encoding_counts.get(name, 0) + 1
            
            # Display as dataframe with actions
            st.subheader("Student Encodings")
            
            for student_id, count in sorted(encoding_counts.items()):
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.write(f"**{student_id}**: {count} encoding(s)")
                
                with col2:
                    if st.button(f"🗑️ Delete", key=f"delete_enc_{student_id}"):
                        if delete_student_encodings(student_id):
                            st.rerun()
                
                with col3:
                    if st.button(f"🔄 Re-encode", key=f"reencode_{student_id}"):
                        with st.spinner(f"Re-encoding {student_id}..."):
                            # Delete old encodings first
                            delete_student_encodings(student_id)
                            # Encode again
                            if encode_student_images(student_id):
                                st.rerun()
            
            st.markdown("---")
            
            # Detailed view
            st.subheader("🔍 Detailed Encoding View")
            selected_student = st.selectbox(
                "Select Student",
                options=sorted(set(names))
            )
            
            if selected_student:
                # Get all encodings for this student
                student_encodings = [
                    embeddings[i] for i, name in enumerate(names) 
                    if name == selected_student
                ]
                
                st.write(f"**{selected_student}** has {len(student_encodings)} encoding(s)")
                
                # Display first encoding as sample
                if student_encodings:
                    st.write("**Sample Encoding (first 20 values):**")
                    sample_values = student_encodings[0][:20]
                    st.code(f"[{', '.join(f'{v:.4f}' for v in sample_values)}...]")
                    
                    # Show encoding statistics
                    all_values = np.array(student_encodings[0])
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Min", f"{all_values.min():.4f}")
                    col2.metric("Max", f"{all_values.max():.4f}")
                    col3.metric("Mean", f"{all_values.mean():.4f}")
                    col4.metric("Std Dev", f"{all_values.std():.4f}")
    
    # Tab 3: Compare (same as before)
    with tab3:
        st.header("🔍 Compare Dataset vs Encodings")
        
        # Students in dataset but not in encodings
        dataset_students = set(dataset_images.keys())
        encoding_students = set(names)
        
        missing_encodings = dataset_students - encoding_students
        extra_encodings = encoding_students - dataset_students
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📁 In Dataset, Missing Encodings")
            if missing_encodings:
                st.error(f"Found {len(missing_encodings)} student(s)")
                for student_id in sorted(missing_encodings):
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.write(f"- {student_id} ({len(dataset_images[student_id])} photos)")
                    with col_b:
                        if st.button(f"🔄 Encode", key=f"encode_missing_{student_id}"):
                            with st.spinner(f"Encoding {student_id}..."):
                                if encode_student_images(student_id):
                                    st.rerun()
            else:
                st.success("✅ All students have encodings")
        
        with col2:
            st.subheader("🧠 In Encodings, Missing Photos")
            if extra_encodings:
                st.warning(f"Found {len(extra_encodings)} student(s)")
                for student_id in sorted(extra_encodings):
                    count = sum(1 for name in names if name == student_id)
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.write(f"- {student_id} ({count} encodings)")
                    with col_b:
                        if st.button(f"🗑️ Delete", key=f"delete_orphan_{student_id}"):
                            if delete_student_encodings(student_id):
                                st.rerun()
            else:
                st.success("✅ All encodings have photos")
    
    # Tab 4: Analysis (same as before)
    with tab4:
        st.header("📊 Dataset Analysis")
        
        if dataset_images and embeddings:
            # Photos per student
            photos_per_student = {
                student_id: len(images)
                for student_id, images in dataset_images.items()
            }
            
            # Encodings per student
            encodings_per_student = {}
            for name in names:
                encodings_per_student[name] = encodings_per_student.get(name, 0) + 1
            
            # Combined dataframe
            all_students = set(photos_per_student.keys()) | set(encodings_per_student.keys())
            
            analysis_data = []
            for student_id in sorted(all_students):
                photos = photos_per_student.get(student_id, 0)
                encodings = encodings_per_student.get(student_id, 0)
                status = "✅" if photos > 0 and encodings > 0 else "❌"
                
                analysis_data.append({
                    "Status": status,
                    "Student ID": student_id,
                    "Photos": photos,
                    "Encodings": encodings,
                    "Match": "✅" if photos == encodings else "⚠️"
                })
            
            df_analysis = pd.DataFrame(analysis_data)
            st.dataframe(df_analysis, use_container_width=True)
            
            # Summary metrics
            col1, col2, col3 = st.columns(3)
            
            perfect_match = sum(1 for row in analysis_data if row["Match"] == "✅")
            has_issues = sum(1 for row in analysis_data if row["Match"] == "⚠️")
            
            col1.metric("✅ Perfect Match", perfect_match)
            col2.metric("⚠️  Has Issues", has_issues)
            col3.metric("🎯 Match Rate", f"{(perfect_match/len(analysis_data)*100):.1f}%" if analysis_data else "N/A")
    
    # Tab 5: Log Monitoring
    with tab5:
        st.header("📝 System Logs Monitor")
        
        # Log controls
        col_control1, col_control2, col_control3 = st.columns([2, 2, 1])
        
        with col_control1:
            log_source = st.selectbox(
                "📂 Log Source",
                ["Face API Logs", "Recognition App Logs", "Attendance CSV"],
                key="log_source"
            )
        
        with col_control2:
            num_lines = st.slider("Number of lines", 10, 500, 100, 10)
        
        with col_control3:
            if st.button("🔄 Refresh", key="refresh_logs"):
                st.rerun()
        
        st.markdown("---")
        
        # Show different logs based on selection
        if log_source == "Face API Logs":
            st.subheader("🤖 Face API Logs")
            
            # Filters
            col_f1, col_f2 = st.columns([1, 3])
            with col_f1:
                level_filter = st.selectbox(
                    "Filter by Level",
                    ["All", "INFO", "WARNING", "ERROR"],
                    key="api_level_filter"
                )
            with col_f2:
                search_query = st.text_input("🔍 Search logs", "", key="api_search")
            
            # Read and display logs
            logs = read_log_file(FACE_API_LOG, num_lines)
            
            if logs:
                # Apply filters
                logs = filter_logs_by_level(logs, level_filter)
                logs = filter_logs_by_search(logs, search_query)
                
                st.info(f"📊 Showing {len(logs)} log entries")
                
                # Display logs with color coding
                for log_line in reversed(logs):  # Show newest first
                    parsed = parse_log_line(log_line)
                    level = parsed['level']
                    
                    if 'ERROR' in level:
                        st.error(f"**{parsed['timestamp']}** | {parsed['message']}")
                    elif 'WARNING' in level:
                        st.warning(f"**{parsed['timestamp']}** | {parsed['message']}")
                    elif 'INFO' in level:
                        st.info(f"**{parsed['timestamp']}** | {parsed['message']}")
                    else:
                        st.text(log_line.strip())
            else:
                st.warning(f"⚠️  No logs found in {FACE_API_LOG}")
        
        elif log_source == "Recognition App Logs":
            st.subheader("👁️ Face Recognition App Logs")
            
            # Filters
            col_f1, col_f2 = st.columns([1, 3])
            with col_f1:
                level_filter = st.selectbox(
                    "Filter by Level",
                    ["All", "INFO", "WARNING", "ERROR"],
                    key="app_level_filter"
                )
            with col_f2:
                search_query = st.text_input("🔍 Search logs", "", key="app_search")
            
            # Read and display logs
            logs = read_log_file(FACE_RECOGNITION_LOG, num_lines)
            
            if logs:
                # Apply filters
                logs = filter_logs_by_level(logs, level_filter)
                logs = filter_logs_by_search(logs, search_query)
                
                st.info(f"📊 Showing {len(logs)} log entries")
                
                # Display logs with color coding
                for log_line in reversed(logs):  # Show newest first
                    parsed = parse_log_line(log_line)
                    level = parsed['level']
                    
                    if 'ERROR' in level:
                        st.error(f"**{parsed['timestamp']}** | {parsed['message']}")
                    elif 'WARNING' in level:
                        st.warning(f"**{parsed['timestamp']}** | {parsed['message']}")
                    elif 'INFO' in level:
                        st.info(f"**{parsed['timestamp']}** | {parsed['message']}")
                    else:
                        st.text(log_line.strip())
            else:
                st.warning(f"⚠️  No logs found in {FACE_RECOGNITION_LOG}")
        
        elif log_source == "Attendance CSV":
            st.subheader("📋 Attendance Records")
            
            # Read CSV
            df = read_attendance_csv(ATTENDANCE_CSV, num_lines)
            
            if not df.empty:
                # Add search filter
                search_student = st.text_input("🔍 Search by Student ID", "", key="csv_search")
                
                if search_student:
                    df = df[df['Student ID'].astype(str).str.contains(search_student, case=False, na=False)]
                
                st.info(f"📊 Showing {len(df)} attendance records")
                
                # Display as dataframe
                st.dataframe(df, use_container_width=True)
                
                # Statistics
                st.markdown("---")
                st.subheader("📊 Quick Stats")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    unique_students = df['Student ID'].nunique()
                    st.metric("Unique Students", unique_students)
                
                with col2:
                    total_records = len(df)
                    st.metric("Total Records", total_records)
                
                with col3:
                    if not df.empty:
                        avg_confidence = df['Confidence'].astype(float).mean()
                        st.metric("Avg Confidence", f"{avg_confidence:.3f}")
                
                # Top students
                if not df.empty:
                    st.markdown("---")
                    st.subheader("🏆 Most Frequent")
                    top_students = df['Student ID'].value_counts().head(10)
                    st.bar_chart(top_students)
            else:
                st.warning(f"⚠️  No attendance records found in {ATTENDANCE_CSV}")
        
        # Auto-refresh option
        st.markdown("---")
        st.caption("💡 Tip: Use the refresh button to see the latest logs in real-time")

if __name__ == "__main__":
    main()