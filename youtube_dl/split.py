import argparse
import os
import datetime
import subprocess
import mp
def download_video(youtube_url, output_file):
    subprocess.run(['youtube-dl', '-o', output_file, youtube_url])

def create_clip(input_file, output_file, start_time, end_time):
    mp.moviepy.io.ffmpeg_extract_subclip(input_file, start_time, end_time, targetname=output_file)

def main():
    parser = argparse.ArgumentParser(description='YouTube Livestream Clip Generator')
    parser.add_argument('url', help='YouTube Livestream URL')
    parser.add_argument('-o', '--output-dir', default='.', help='Output directory for the clip')
    args = parser.parse_args()

    # Get current time
    current_time = datetime.datetime.now()
    end_time = current_time.strftime("%H:%M:%S")

    # Calculate start time (2 minutes before the current time)
    start_time_delta = datetime.timedelta(minutes=2)
    start_time = (current_time - start_time_delta).strftime("%H:%M:%S")

    # Define filenames and paths
    output_filename = 'output.mp4'
    output_path = os.path.join(args.output_dir, output_filename)

    # Download the video
    download_video(args.url, output_path)

    # Create the clip
    create_clip(output_path, output_path, start_time, end_time)

if __name__ == "__main__":
    main()
