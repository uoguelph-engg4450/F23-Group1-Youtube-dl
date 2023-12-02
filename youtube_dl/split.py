#Splits livestream into clips with defined lengths
#

#Reference sources
#   https://www.knowledgehut.com/blog/programming/sys-argv-python-examples
#   https://artwilton.medium.com/running-ffmpeg-commands-from-a-python-script-676eaf2b2739

#if testing use the output from python youtube_dl -g <url>

import sys
import subprocess
import getopt

def split_live(duration = "00:01:00.00", numClips = 1, ffmpeg = None):
    argv = sys.argv[1:]

    #for test runs
    if argv != None:
        url = argv[0]
        duration = argv[1]
        numClips = argv[2]

        #set ffmpeg location if needed
        opt, arg = getopt.getopt(argv, "f", "ffmpeg=")

    for name, value in opt:
        if name in ['-f', '--ffmpeg']:
            ffmpeg = value

    commands = [ffmpeg, '-i', url, '-t', duration, '-c', "copy", "clip.mp4"]

    for i in numClips:
        clipName = "clip" + str(i) +".mp4"
        commands[7] = clipName

        if subprocess.run(commands).returncode != 0:
            print("Split livestream error")
            return 0
    
    print("Livestream clips downloaded")

