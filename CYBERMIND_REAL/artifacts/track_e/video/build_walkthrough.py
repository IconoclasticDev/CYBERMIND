"""Create a captioned sequence of actual captured UI states; no simulated recording."""
from pathlib import Path
import hashlib,json,subprocess
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
BUILD=OUT/'walkthrough_build'; BUILD.mkdir(exist_ok=True)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',29)
small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
scenes=[
 ('../slides/preview/slide-1.png',10,'CYBERMIND analyst walkthrough','Edited sequence of captured UI states. Synthetic verification data; silent captions.'),
 ('../slides/preview/slide-2.png',10,'Production architecture','60-second graph windows feed the temporal model. This demo uses a separate synthetic fixture.'),
 ('01-overview.png',12,'Observed network and forecast','The local console displays two observed hosts and stochastic risk across future windows.'),
 ('02-isolation.png',12,'Compare a host isolation probe','The probe removes incident edges while preserving measured features, history and random draws.'),
 ('03-isolation-table.png',12,'No measured reduction in this case','Baseline and probe both return 0.749606 risk. The UI reports no beneficial simulated isolation.'),
 ('../slides/preview/slide-4.png',10,'Model sensitivity has limits','This comparison does not estimate causal containment effects or execute a network action.'),
 ('../slides/preview/slide-5.png',14,'Evidence boundary','Phase 3 passes under the reviewed protocol on synthetic verification data. Real accuracy remains unmeasured.'),
]
manifest=[]
def wrap(draw,text,width):
 words=text.split(); lines=[]; line=''
 for word in words:
  test=(line+' '+word).strip()
  if draw.textlength(test,font=font)>width and line: lines.append(line); line=word
  else:line=test
 lines.append(line);return lines
for i,(source,duration,title,caption) in enumerate(scenes):
 source=(OUT/source).resolve(); original=Image.open(source).convert('RGB')
 frame=Image.new('RGB',(1600,900),'#0e1725')
 # Resize to fit without cropping; screenshot content remains unchanged.
 original.thumbnail((1600,720),Image.Resampling.LANCZOS)
 frame.paste(original,((1600-original.width)//2,(720-original.height)//2))
 draw=ImageDraw.Draw(frame);draw.rectangle((0,720,1600,900),fill='#08101c')
 draw.text((40,737),title,font=font,fill='#90d8e8')
 for j,line in enumerate(wrap(draw,caption,1510)):
  draw.text((40,780+j*35),line,font=font,fill='white')
 draw.text((40,870),f'CAPTURED UI WALKTHROUGH  |  SYNTHETIC EVIDENCE  |  {i+1}/{len(scenes)}',font=small,fill='#a8b8c9')
 dest=BUILD/f'scene-{i+1}.png';frame.save(dest)
 manifest.append({'source':str(source.relative_to(ROOT)), 'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'duration_seconds':duration,'title':title,'caption':caption})
concat=BUILD/'scenes.txt'
concat.write_text(''.join(f"file 'scene-{i+1}.png'\nduration {scene[1]}\n" for i,scene in enumerate(scenes))+f"file 'scene-{len(scenes)}.png'\n",encoding='utf-8')
ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
output=OUT/'CYBERMIND_demo.mp4'
subprocess.run([ffmpeg,'-y','-f','concat','-safe','0','-i',str(concat),'-t',str(sum(s[1] for s in scenes)),'-vf','fps=24','-c:v','libx264','-crf','20','-preset','medium','-pix_fmt','yuv420p','-movflags','+faststart',str(output)],check=True,capture_output=True)
reader=imageio_ffmpeg.read_frames(str(output),pix_fmt='rgb24');metadata=next(reader)
assert metadata['size']==(1600,900),metadata
assert abs(metadata['duration']-80)<.1,metadata
frame_count=0; selected=[]
for raw in reader:
 if frame_count in [120,600,960,1200,1680]:
  path=BUILD/f'decoded-{frame_count}.png';Image.frombytes('RGB',(1600,900),raw).save(path);selected.append(str(path.relative_to(ROOT)))
 frame_count+=1
assert frame_count==1920,frame_count
report={'passed':True,'format':'Edited still-image walkthrough; not continuous screen recording','audio':'None; burned captions','duration_seconds':metadata['duration'],'resolution':metadata['size'],'fps':metadata['fps'],'decoded_frames':frame_count,'output_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'scenes':manifest,'inspected_frame_files':selected}
(OUT/'video_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ['scenes','inspected_frame_files']},indent=2))

