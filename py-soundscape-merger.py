import os
import sys
import subprocess
import concurrent.futures
from tqdm import tqdm

def build_ffmpeg_command(audiobook_path, soundscape_path, output_path):
    filter_complex_str = (
        "[1:a]aformat=channel_layouts=stereo,volume=0.9[bg];"
        "[bg]aecho=0.8:0.6:60:0.3[bgRev];"
        "[bgRev]channelsplit=channel_layout=stereo[bgRevL][bgRevR];"
        "[bgRevL]asplit=2[bgRevFL][bgRevBL];"
        "[bgRevR]asplit=2[bgRevFR][bgRevBR];"
        "[bgRevBL]adelay=100|100[bgRearL];"
        "[bgRevBR]adelay=100|100[bgRearR];"
        "[bgRev]lowpass=f=115[bgLFE];"
        "[0:a]aformat=channel_layouts=stereo,channelsplit=channel_layout=stereo[a0L][a0R];"
        "[a0L][a0R]amerge=inputs=2,pan=mono|c0<0.5c0+0.5c1[a0mono];"
        "[bgRevFL][bgRevFR][a0mono][bgLFE][bgRearL][bgRearR]amerge=inputs=6[aout]"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-i", audiobook_path,
        "-i", soundscape_path,
        "-map_metadata", "0",
        "-map", "0:v?",
        "-filter_complex", filter_complex_str,
        "-map", "[aout]",
        "-c:v", "copy", 
        "-c:a", "aac",
        "-b:a", "384k",
        "-ac", "6",
        output_path
    ]
    return cmd

def run_ffmpeg_command(cmd):
    # Suppress FFmpeg output
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

def merge_chapters_by_order(audiobook_folder, soundscape_folder, output_folder, max_workers=4):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    audiobook_files = sorted([f for f in os.listdir(audiobook_folder) if f.lower().endswith(".mp3")])
    soundscape_files = sorted([f for f in os.listdir(soundscape_folder) if f.lower().endswith(".mp3")])

    count = min(len(audiobook_files), len(soundscape_files))

    commands = []
    for i in range(count):
        audiobook_file = audiobook_files[i]
        soundscape_file = soundscape_files[i]
        audiobook_path = os.path.join(audiobook_folder, audiobook_file)
        soundscape_path = os.path.join(soundscape_folder, soundscape_file)

        base_name_no_ext = os.path.splitext(audiobook_file)[0]
        output_file_name = f"{base_name_no_ext}_5.1.mp4"
        output_path = os.path.join(output_folder, output_file_name)

        cmd = build_ffmpeg_command(audiobook_path, soundscape_path, output_path)
        commands.append(cmd)

    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = [executor.submit(run_ffmpeg_command, cmd) for cmd in commands]

        # Track overall progress with tqdm
        with tqdm(total=len(futures), desc="Merging chapters", unit="file") as pbar:
            for _ in concurrent.futures.as_completed(futures):
                pbar.update(1)

def main():
    if len(sys.argv) < 4:
        print(f"Usage: {sys.argv[0]} <audiobook_folder> <soundscape_folder> <output_folder> [max_workers]")
        sys.exit(1)

    audiobook_folder = sys.argv[1]
    soundscape_folder = sys.argv[2]
    output_folder = sys.argv[3]
    max_workers = int(sys.argv[4]) if len(sys.argv) > 4 else 4

    merge_chapters_by_order(audiobook_folder, soundscape_folder, output_folder, max_workers)

if __name__ == "__main__":
    main()
