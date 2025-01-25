import os
import glob
import sys

from moviepy.editor import VideoFileClip
import pandas as pd
import matplotlib.pyplot as plt
import json
import cv2
import mediapipe as mp
import numpy as np

# Function to create a cropped video of the top-right quarter
def create_stimuli_video(input_video_path, output_video_path):
    with VideoFileClip(input_video_path) as video_clip:
        # Get the width and height of the original video
        width, height = video_clip.size
        # Crop the video to the top-right quarter
        cropped_clip = video_clip.crop(x1=(3 * width) // 4, y1=0, x2=width, y2=height // 4)
        # Save the cropped video
        cropped_clip.write_videofile(output_video_path, fps=video_clip.fps, codec='libx264')
        cropped_clip.close()


# Function to trim 1 second from the start and end of the video
def trim_video(input_video_path, output_video_path):
    with VideoFileClip(input_video_path) as video_clip:
        # Trim 1 second from start and end
        duration = video_clip.duration
        trimmed_clip = video_clip.subclip(1, max(0, duration - 1))
        # Save the trimmed video
        trimmed_clip.write_videofile(output_video_path, fps=video_clip.fps, codec='libx264')
        trimmed_clip.close()


# Fonction pour traiter les résultats PyAFAR et les exporter en CSV
def process_infant_video(input_mp4, csv_filename):
    from PyAFAR_GUI.infant_afar import infant_afar

    # Appliquer l'analyse PyAFAR
    infant_result = infant_afar(filename=input_mp4, AUs=["au_1", "au_2", "au_3", "au_4", "au_6", "au_9", "au_12", "au_20", "au_28"], GPU=False, max_frames=1000)

    # Création d'un DataFrame à partir des résultats (supposons que infant_result soit un DataFrame ou convertible en DataFrame)
    infant_pyafar = pd.DataFrame(infant_result)

    # Sauvegarder le DataFrame en CSV
    infant_pyafar.to_csv(csv_filename, index=False)
    return infant_pyafar


def process_stimuli_video(input_mp4, csv_filename, json_filename, df_stim_landmarks):
    from PyAFAR_GUI.adult_afar import adult_afar

    # Run adult AFAR
    adult_result = adult_afar(filename=input_mp4, AUs=["au_1", "au_2", "au_4", "au_6", "au_7", "au_10", "au_12",
                                                       "au_14", "au_15", "au_17", "au_23", "au_24"],
                              AU_Int=[], GPU=True, max_frames=1000, batch_size=100, PID=False)

    # Create a DataFrame from the results
    df = pd.DataFrame(adult_result)

    # Save the DataFrame as CSV
    df.to_csv(csv_filename, index=False)

    # Find start and stop of the experiment
    start_frame = df.iloc[0]['Frame']
    end_frame = df.iloc[-1]['Frame']

    # Detect trial epochs using frame continuity
    epoch_starts = []
    epoch_ends = []

    current_start = int(df['Frame'].iloc[0])
    for i in range(1, len(df)):
        if df.iloc[i]['Frame'] != df.iloc[i - 1]['Frame'] + 1:
            epoch_starts.append(current_start)
            epoch_ends.append(int(df.iloc[i - 1]['Frame']))
            current_start = int(df.iloc[i]['Frame'])

    # Add the last epoch
    epoch_starts.append(current_start)
    epoch_ends.append(int(df['Frame'].iloc[-1]))

    for i in range(len(epoch_starts)):
        epoch_start = epoch_starts[i]
        epoch_end = epoch_ends[i]

        if (epoch_end - epoch_start) > 500:
            # Filter data for the relevant frames
            filtered_stim_landmarks_df = df_stim_landmarks[df_stim_landmarks['frame'].between(epoch_start, epoch_end)]

            z_scored_diffs = []

            # Loop through all landmark indices
            for landmark_idx in range(478):  # 0 to 477 inclusive
                # Filter data for the current landmark_index
                landmark_data = filtered_stim_landmarks_df[filtered_stim_landmarks_df['landmark_index'] == landmark_idx]

                if landmark_data.empty:
                    continue

                # Sort data by frame to ensure proper sequential order
                landmark_data = landmark_data.sort_values(by='frame')

                # Compute the Euclidean distance to the previous frame's coordinates
                previous_coords = landmark_data[['x', 'y', 'z']].shift(1)
                landmark_data['distance_to_previous'] = np.sqrt(
                    (landmark_data['x'] - previous_coords['x']) ** 2 +
                    (landmark_data['y'] - previous_coords['y']) ** 2 +
                    (landmark_data['z'] - previous_coords['z']) ** 2
                )

                # Drop NaN values introduced by the shift operation
                landmark_data = landmark_data.dropna(subset=['distance_to_previous'])

                # Compute the z-scored difference
                dist_change = np.abs(np.diff(landmark_data['distance_to_previous']))
                if dist_change.size > 0:
                    z_scored_diffs.append((dist_change - np.mean(dist_change)) / np.std(dist_change))

            # Compute the average z-scored difference across all landmark indices
            average_z_scored_diff = np.nanmean(np.array(z_scored_diffs), axis=0)

            # Identify frames where averaged_z_scored_diff > 5
            unique_frames = np.array(sorted(filtered_stim_landmarks_df['frame'].unique()))[2:]
            significant_frames = unique_frames[average_z_scored_diff > 5]

            # Split epochs based on significant frames, but only for epochs longer than 500 frames
            frame = significant_frames[0]
            epoch_ends[i] = frame - 1
            epoch_starts.insert(i + 1, frame)
            epoch_ends.insert(i + 1, epoch_ends[i])

    # Create a JSON file with updated frame information
    frame_info = {
        "start_frame": int(start_frame),
        "end_frame": int(end_frame),
        "epoch_starts": [int(frame) for frame in epoch_starts],
        "epoch_ends": [int(frame) for frame in epoch_ends]
    }

    with open(json_filename, 'w') as json_file:
        json.dump(frame_info, json_file, indent=4)

    return frame_info, df


def epoch_stimuli(log_file, frame_info, json_filename, emotion_column="emotion", actor_column='actor'):

    # Charger le fichier contenant les émotions
    log_df = pd.read_csv(log_file, sep='\t')

    # Vérifier si la colonne d'émotion existe
    if emotion_column not in log_df.columns:
        raise ValueError(f"La colonne '{emotion_column}' n'existe pas dans le fichier '{log_file}'.")
    if actor_column not in log_df.columns:
        raise ValueError(f"La colonne '{actor_column}' n'existe pas dans le fichier '{log_file}'.")

     #vérifier que le nombre d'epochs correspond à la longueur des emotions
    num_epochs = len(frame_info["epoch_starts"])
    num_emotions = len(log_df)

    if num_emotions < num_epochs:
        raise ValueError("Le fichier d'émotion contient moins de lignes que le nombre d'epochs.")
    elif num_emotions > num_epochs:
        print(f"Attention : Le fichier contient {num_emotions} émotions, mais seulement {num_epochs} epochs.")

   # Associer les émotions aux epochs
    epochs = []
    for i in range(num_epochs):
        epoch_data = {
            "epoch_number": i + 1,
            "epoch_start": frame_info["epoch_starts"][i],
            "epoch_end": frame_info["epoch_ends"][i],
            "emotion": log_df[emotion_column].iloc[i],
            "actor": log_df[actor_column].iloc[i]
        }
        epochs.append(epoch_data)

    # Convertir en JSON
    with open(json_filename, 'w') as json_file:
        json.dump(epochs, json_file, indent=4)
    return epochs


def run_mediapipe(input_mp4, output_video_path, output_landmarks):
    # Initialize MediaPipe Face Mesh
    mp_drawing = mp.solutions.drawing_utils
    mp_face_mesh = mp.solutions.face_mesh
    mp_drawing_styles = mp.solutions.drawing_styles

    face_mesh = mp_face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    drawing_spec = mp_drawing.DrawingSpec(thickness=1, circle_radius=1)

    # List to store landmark data
    landmarks_list = []

    # Open the video with moviepy
    clip = VideoFileClip(input_mp4)

    def process_frame(frame):
        # Make the frame writable (copy the read-only frame)
        writable_frame = frame.copy()

        # Process the frame with Face Mesh
        results = face_mesh.process(writable_frame)

        # Check if landmarks were detected
        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0]

            # Store landmark data
            for idx, landmark in enumerate(landmarks.landmark):
                landmarks_list.append({
                    "frame": int(clip.reader.pos),
                    "landmark_index": idx,
                    "x": landmark.x,
                    "y": landmark.y,
                    "z": landmark.z
                })

            # Annotate the frame
            mp_drawing.draw_landmarks(
                image=writable_frame,
                landmark_list=results.multi_face_landmarks[0],
                connections=mp_face_mesh.FACEMESH_TESSELATION,
                landmark_drawing_spec=drawing_spec,
                connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_tesselation_style()
            )

        return writable_frame

    # Process the video and write the annotated frames
    processed_clip = clip.fl_image(process_frame)
    processed_clip.write_videofile(output_video_path, codec="libx264", fps=clip.fps)

    # Convert landmarks list to DataFrame and save as CSV
    df = pd.DataFrame(landmarks_list)

    # Release resources
    face_mesh.close()

    df.to_csv(output_landmarks)
    return df


def fix_outliers(df_pyafar, df_landmarks, frame_info):
    # Filtrer pour ne garder que les frames à partir de start_frame
    df_filtered_landmarks = df_landmarks[df_landmarks['frame'] >= frame_info['start_frame']]

    outlier_frames = distance_outliers(df_filtered_landmarks)

    columns_to_fix = [col for col in df_pyafar.columns if 'au' in col]
    df_pyafar.loc[df_pyafar['Frame'].isin(outlier_frames), columns_to_fix] = np.nan
    return df_pyafar


def distance_outliers(df_landmarks):
    # Calculer la distance pour chaque frame
    distances = []
    for frame_num in df_landmarks['frame'].unique():
        frame_data = df_landmarks[df_landmarks['frame'] == frame_num]
        # Calcul de la distance pour chaque frame en utilisant x(max) - x(min), y(max) - y(min), z(max) - z(min)
        x_distance = frame_data['x'].max() - frame_data['x'].min()
        y_distance = frame_data['y'].max() - frame_data['y'].min()
        z_distance = frame_data['z'].max() - frame_data['z'].min()
        distances.append({'frame': frame_num, 'x_diff': x_distance, 'y_diff': y_distance, 'z_diff': z_distance})

    # Convertir les distances en DataFrame pour une analyse statistique
    df_distances = pd.DataFrame(distances)

    # Calculer la moyenne et l'écart-type pour chaque axe
    mean_x, std_x = df_distances["x_diff"].mean(), df_distances["x_diff"].std()
    mean_y, std_y = df_distances["y_diff"].mean(), df_distances["y_diff"].std()
    mean_z, std_z = df_distances["z_diff"].mean(), df_distances["z_diff"].std()

    # Identification des frames hors des limites
    outlier_frames = df_distances[
        ((df_distances["x_diff"] < mean_x - 2 * std_x) | (df_distances["x_diff"] > mean_x + 2 * std_x)) |
        ((df_distances["y_diff"] < mean_y - 2 * std_y) | (df_distances["y_diff"] > mean_y + 2 * std_y)) |
        ((df_distances["z_diff"] < mean_z - 2 * std_z) | (df_distances["z_diff"] > mean_z + 2 * std_z))
        ]["frame"].values

    return outlier_frames


def epoch_pyafar(df_pyafar, epoch_data, epoched_csv_fname, filtered_csv_path):
    # Charger les données du fichier CSV PyAFAR
    print(df_pyafar.columns)

    # Vérifier si la colonne "frame" existe
    if "Frame" not in df_pyafar.columns:
        raise ValueError(f"La colonne 'frame' est absente du fichier CSV {df_pyafar}.")

    # Ajouter les colonnes des epochs et des émotions
    df_pyafar["epoch_number"] = -1
    df_pyafar["emotion"] = -1
    df_pyafar["actor"] = -1

    # Appliquer les informations des epochs en se basant sur la colonne "frame"
    for epoch in epoch_data:
        start_frame = epoch["epoch_start"]
        end_frame = epoch["epoch_end"]
        emotion = epoch["emotion"]
        actor = epoch["actor"]

        # Marquer les frames comprises dans cet epoch
        df_pyafar.loc[(df_pyafar["Frame"] >= start_frame) & (df_pyafar["Frame"] <= end_frame), "epoch_number"] = epoch["epoch_number"]
        df_pyafar.loc[(df_pyafar["Frame"] >= start_frame) & (df_pyafar["Frame"] <= end_frame), "emotion"] = emotion
        df_pyafar.loc[(df_pyafar["Frame"] >= start_frame) & (df_pyafar["Frame"] <= end_frame), "actor"] = actor

    df_pyafar.to_csv(epoched_csv_fname)

    # Créer un DataFrame filtré contenant uniquement les frames avec un numéro d'epoch valide
    df_filtered_pyafar = df_pyafar[df_pyafar["epoch_number"] != -1]

    df_filtered_pyafar.to_csv(filtered_csv_path)


def process_session_infant_et_video(subj_id, ses_id, et_data_dir, output_dir):
    vid_files = glob.glob(os.path.join(et_data_dir, '*.mkv'))
    if len(vid_files) == 0:
        print('{} eyetracking - missing video'.format(ses_id))
    base_video = vid_files[0]

    et_data_files = glob.glob(os.path.join(et_data_dir, '*_eyetracking.tsv'))
    if len(et_data_files) == 0:
        print('{} eyetracking - no eyetracking data'.format(ses_id))
    for et_data_file in et_data_files:
        log_file = os.path.join(et_data_dir, '{}.tsv'.format(
            '_'.join(os.path.split(os.path.splitext(et_data_file)[0])[1].split('_')[0:-1])))
        if not os.path.exists(log_file):
            print('{} eyetracking, {} - no log file'.format(ses_id, os.path.split(et_data_file)[-1]))

    print(base_video)
    print(log_file)

    # Trimmer 1 seconde au début et à la fin de la vidéo MP4 originale
    trimmed_output_mp4 = os.path.join(output_dir, f"{subj_id}_{ses_id}_trimmed.mp4")
    trim_video(base_video, trimmed_output_mp4)

    ## Stimulus video
    # Création de la vidéo "stimuli" contenant uniquement le quart supérieur droit
    output_stimuli_video = os.path.join(output_dir, f"{subj_id}_{ses_id}_stimuli.mp4")
    create_stimuli_video(trimmed_output_mp4, output_stimuli_video)

    output_stim_landmarks_video = os.path.join(output_dir, f"{subj_id}_{ses_id}_stimuli_landmarks.mp4")
    output_stim_landmarks = os.path.join(output_dir, f"{subj_id}_{ses_id}_stimuli_landmarks.csv")
    df_stim_landmarks = run_mediapipe(output_stimuli_video, output_stim_landmarks_video, output_stim_landmarks)

    stim_pyafar_fname = os.path.join(output_dir, f"{subj_id}_{ses_id}_stimuli.csv")
    stim_info_filename = os.path.join(output_dir, f"{subj_id}_{ses_id}_stimuli_info.json")
    frame_info, stimuli_pyafar = process_stimuli_video(output_stimuli_video, stim_pyafar_fname, stim_info_filename,
                                                       df_stim_landmarks)

    stim_epoch_fname = os.path.join(output_dir, f"{subj_id}_{ses_id}_stimuli_epochs.json")
    epoch_data = epoch_stimuli(log_file, frame_info, stim_epoch_fname)

    stim_pyafar_filtered_fname = os.path.join(output_dir, f"{subj_id}_{ses_id}_stimuli_pyafar_epochs.csv")
    epoch_pyafar(stimuli_pyafar, epoch_data, stim_pyafar_fname, stim_pyafar_filtered_fname)

    ## Infant video
    output_infant_landmarks_video = os.path.join(output_dir, f"{subj_id}_{ses_id}_infant_landmarks.mp4")
    output_infant_landmarks = os.path.join(output_dir, f"{subj_id}_{ses_id}_infant_landmarks.csv")
    df_infant_landmarks = run_mediapipe(trimmed_output_mp4, output_infant_landmarks_video, output_infant_landmarks)

    # Process PyAFAR et export CSV pour la vidéo trimée originale
    infant_pyafar_fname = os.path.join(output_dir, f"{subj_id}_{ses_id}_infant.csv")
    infant_pyafar = process_infant_video(trimmed_output_mp4, infant_pyafar_fname)

    infant_pyafar_fixed = fix_outliers(infant_pyafar, df_infant_landmarks, frame_info)

    infant_pyafar_filtered_fname = os.path.join(output_dir, f"{subj_id}_{ses_id}_infant_pyafar_epochs.csv")
    epoch_pyafar(infant_pyafar_fixed, epoch_data, infant_pyafar_fname, infant_pyafar_filtered_fname)


if __name__=='__main__':
    subj_id = sys.argv[1]
    ses_id = sys.argv[2]

    raw_path = '/home/common/bonaiuto/devmobeta/data/'
    deriv_path = '/home/common/bonaiuto/devmobeta/derivatives/'

    et_data_dir = os.path.join(raw_path, subj_id, ses_id, 'eyetracking')
    output_dir = os.path.join(deriv_path, subj_id, ses_id, 'eyetracking')
    os.makedirs(output_dir, exist_ok=True)

    process_session_infant_et_video(subj_id, ses_id, et_data_dir, output_dir)





