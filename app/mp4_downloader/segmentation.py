import os
import re
import subprocess
import logging


def verify_segments(segmentation_path, logger=None):
    if logger is None:
        logger = logging.getLogger("Segmentation Verifier")
    else:
        logger = logger
    try:
        ts_files = [f for f in os.listdir(segmentation_path) if f.endswith(".ts")]
        if not ts_files:
            raise ValueError("Aucun segment .ts trouvé")

        numbers = [int(re.search(r'(\d+)', f).group(1)) for f in ts_files if re.search(r'(\d+)', f)]
        expected_numbers = set(range(1, max(numbers) + 1))
        missing_numbers = expected_numbers - set(numbers)
            
        if missing_numbers:
            raise ValueError(f"Segments manquants : {sorted(missing_numbers)}")

        for ts_file in ts_files:
            if os.path.getsize(os.path.join(segmentation_path, ts_file)) == 0:
                raise ValueError(f"Le segment {ts_file} est vide")

        logger.info(f"Vérification des segments réussie : {len(ts_files)} segments valides")
        return True

    except Exception as e:
        logger.error(f"Erreur lors de la vérification des segments : {str(e)}")
        return False

def merge_segments(path, temps_path, logger=None):
    if logger is None:
        logger = logging.getLogger("Segmentation Merger")
    else:
        logger = logger
    try:
        file_list_path = os.path.join(temps_path, "segments.txt")
        segmentation_path = os.path.join(temps_path, "segmentation")
            
        if not verify_segments(segmentation_path):
            raise ValueError("Les segments ne sont pas valides")
            
        if not os.path.exists(file_list_path):
            raise FileNotFoundError(f"Le fichier de liste {file_list_path} n'existe pas")

        os.makedirs(os.path.dirname(path), exist_ok=True)
        temp_ts_path = os.path.join(temps_path, "temp_output.ts")
            
        # Fusion en .ts
        merge_command = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", file_list_path,
            "-c", "copy",
            "-fflags", "+genpts+igndts",
            "-vsync", "0",
            "-max_interleave_delta", "0",
            "-async", "1",
            "-fflags", "+genpts+igndts+discardcorrupt",
            "-avoid_negative_ts", "make_zero",
            "-y",
            temp_ts_path
        ]
            
        subprocess.run(merge_command, check=True, capture_output=True, text=True)
            
        if not os.path.exists(temp_ts_path) or os.path.getsize(temp_ts_path) == 0:
            raise ValueError("Le fichier temporaire .ts n'a pas été créé correctement")

        # Conversion en .mp4
        convert_command = [
            "ffmpeg",
            "-i", temp_ts_path,
            "-c", "copy",
            "-movflags", "+faststart",
            "-y",
            path
        ]
            
        subprocess.run(convert_command, check=True, capture_output=True, text=True)
            
        # Nettoyage
        if os.path.exists(temp_ts_path):
            os.remove(temp_ts_path)
            
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            raise ValueError("Le fichier de sortie n'a pas été créé correctement")
                
        logger.info("Les segments ont été fusionnés avec succès")
        return True
            
    except subprocess.CalledProcessError as e:
        logger.error(f"Erreur lors de la fusion des segments: {e.stderr}")
        return False
        raise
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la fusion des segments: {str(e)}")
        return False
        raise