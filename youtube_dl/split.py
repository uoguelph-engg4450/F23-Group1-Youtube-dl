#Splits livestream into clips with defined lengths
#

#Reference sources
#   https://www.knowledgehut.com/blog/programming/sys-argv-python-examples
#   https://artwilton.medium.com/running-ffmpeg-commands-from-a-python-script-676eaf2b2739

#if testing use the output from python youtube_dl -g <url>

import sys
import subprocess
import getopt

default_url = "https://manifest.googlevideo.com/api/manifest/hls_playlist/expire/1701512187/ei/m69qZfDiHeKX2_gPnreS6A8/ip/64.229.43.235/id/jfKfPfyJRdk.2/itag/96/source/yt_live_broadcast/requiressl/yes/ratebypass/yes/live/1/sgoap/gir%3Dyes%3Bitag%3D140/sgovp/gir%3Dyes%3Bitag%3D137/rqh/1/hls_chunk_host/rr2---sn-cxaaj5o5q5-t34l.googlevideo.com/xpc/EgVo2aDSNQ%3D%3D/playlist_duration/30/manifest_duration/30/spc/UWF9f7Pyl95o9A3VLizSSUApyGTWt6Cj_wQmPSZlUQ/vprv/1/playlist_type/DVR/mh/rr/mm/44/mn/sn-cxaaj5o5q5-t34l/ms/lva/mv/u/mvi/2/pl/27/dover/11/pacing/0/keepalive/yes/fexp/24007246/mt/1701489735/sparams/expire,ei,ip,id,itag,source,requiressl,ratebypass,live,sgoap,sgovp,rqh,xpc,playlist_duration,manifest_duration,spc,vprv,playlist_type/sig/ANLwegAwRAIgIgsZq9-Cv5tY_vKt7Gt_y_fnemrznfbWxphmURn0R6ACIG5xC572UwrPpLKyyFJzbByYTDNRsShVykBo4ENZq1Fj/lsparams/hls_chunk_host,mh,mm,mn,ms,mv,mvi,pl/lsig/AM8Gb2swRgIhAMJ00ThGc3YSY-gGrN3-VdaANTN-TKuiXRfDoX3WjPhQAiEAso97lm9JcsJgj1bKdiIbR582UWXuKbczCExGdn6Zpf0%3D/playlist/index.m3u8"

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

def split_live(duration = "00:01:00.00", numClips = 1, ffmpeg = None, url = default_url):

    commands = [ffmpeg, '-i', url, '-t', duration, '-c', "copy", "clip.mp4"]

    for i in numClips:
        clipName = "clip" + str(i) +".mp4"
        commands[7] = clipName

        if subprocess.run(commands).returncode != 0:
            print("Split livestream error")
            return 0
    
    print("Livestream clips downloaded")

split_live(duration, numClips, ffmpeg, url)