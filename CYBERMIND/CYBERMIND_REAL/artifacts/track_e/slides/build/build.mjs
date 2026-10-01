import fs from 'node:fs/promises';
import path from 'node:path';
import {Presentation, PresentationFile} from '@oai/artifact-tool';
import {resolvePresentationFont,finalizePresentation} from 'file:///C:/Users/as030/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations/container_tools/artifact_tool_utils.mjs';
const work=path.resolve('artifacts/track_e/slides');
const skill='C:/Users/as030/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations';
const font=resolvePresentationFont({fontFamily:'Arial'});
const p=Presentation.create({slideSize:{width:1280,height:720}});
function text(s,t,x,y,w,h,size=28,color='#E8EEF4',bold=false){const a=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});a.text=t;a.text.style={typeface:font,fontSize:size,color,bold,autoFit:'none'};return a;}
function slide(title,note){let s=p.slides.add();s.background.fill='#0E1725';text(s,title,66,45,1148,85,46,'#FFFFFF',true);s.speakerNotes.textFrame.setText(note);return s;}
let s=slide('CYBERMIND: analyst decision support','Sources: docs/SIH26153_CYBERMIND_Master_Plan.md, docs/TRACK_B_ANALYST_UI_AUDIT.md. Proposed workflow; operational benefit is not yet measured.');
text(s,'Alerts describe events. Analysts still need context\nto decide what to inspect next.',68,166,1090,125,40,'#90D8E8');
text(s,'Observed network  →  future risk  →  sensitivity comparison',68,350,1140,65,32,'#FFFFFF',true);
text(s,'The local console connects the forecast to its input graph,\nmodel explanation and checkpoint lineage.',68,450,1060,100,30);
text(s,'Prototype demonstration • Synthetic verification data',68,630,1100,38,22,'#A8B8C9');
s=slide('Temporal graph architecture','Sources: configs/gb10_full.yaml; src/cybermind/models/world_model.py; src/cybermind/models/stage_decoder.py. Production configuration uses 60-second windows, 30-second stride, history16. Synthetic verification uses its separate fixture configuration.');
text(s,'60-second graph windows',68,165,1090,60,39,'#90D8E8',true);
text(s,'Hosts form nodes; flows and packet telemetry describe edges.\nA 30-second stride preserves overlap across 16 observed windows.',68,245,1120,100,29);
text(s,'Edge-aware GATv2   →   temporal Transformer',68,383,1120,60,34,'#FFFFFF',true);
text(s,'Latent dynamics produce risk rollouts and stage emissions.\nThe CRF constrains decoded transitions to the reviewed policy.',68,470,1120,95,29);
text(s,'Packet-complete preparation remains a prerequisite for the production run.',68,629,1120,45,23,'#A8B8C9');
s=slide('Analyst console: actual local inference','Source image: artifacts/track_e/video/01-overview.png, captured from locally running scripts/app.py. Reviewed epoch185 checkpoint, synthetic test sequence0; no real-data accuracy is implied.');
s.images.add({blob:new Uint8Array(await fs.readFile('artifacts/track_e/video/01-overview.png')),contentType:'image/png',alt:'Actual CYBERMIND analyst console showing network, forecast and intervention controls',fit:'contain',position:{left:66,top:142,width:1148,height:480}});
text(s,'Observed topology, named forecast steps, uncertainty and case lineage',68,643,1135,38,25,'#90D8E8');
s=slide('Isolation probe: no measured risk reduction','Sources: current scripts/app.py; src/cybermind/analyst/view.py; root Track E corrected isolation verification. Same checkpoint, observed history and random draws. Incident-edge removal preserves measured node features. Earlier feature scaling increased risk and was an intervention-semantics defect, not evidence that physical isolation worsens security.');
text(s,'74.96%  →  74.96%',68,170,1130,100,66,'#90D8E8',true);
text(s,'Baseline risk          Edge-cut probe',70,279,1100,48,30);
text(s,'The corrected probe removes incident edges while retaining\nmeasured node features, history and random draws.',68,388,1115,96,30);
text(s,'This case supplies no evidence of a helpful action.\nThe comparison measures model sensitivity, not causality.',68,520,1110,100,31,'#FFFFFF',true);
s=slide('Evidence and the next gate','Sources: PHASE3_FINAL_AUDIT.md; docs/TRACK_A_BENCHMARK_AUDIT.md; examples/track_a_benchmark/selected185/comparison.json; current Phase4 and Track C/D audit status. Synthetic table covers25 targets(19 negatives,6 positives), one-step infiltration threshold0.5. Feature-matched logistic baseline ties the selected world model: F1=1,FPR=0. Epoch98 and200 fail step1 whereas selected185 passes. No superiority or real-data kill-chain accuracy claim.');
text(s,'Phase 3 passes under the reviewed protocol\non synthetic verification data',68,160,1120,100,34,'#90D8E8',true);
text(s,'Epoch 185 passes all four steps; epochs 98 and 200 fail step 1.\nThe result is a narrow selected checkpoint, not a stable plateau.',68,299,1115,100,28);
text(s,'Feature-matched baseline and world model tie: F1 1.00, FPR 0.00.\nReal-data accuracy and superiority remain unmeasured.',68,429,1115,95,28);
text(s,'Next gate: validate the one-day packet/flow join and labels\nbefore a separately authorized production training run.',68,563,1115,95,29,'#FFFFFF',true);
const candidate=path.join(work,'build/candidate.pptx');await(await PresentationFile.exportPptx(p)).save(candidate);
for(let i=0;i<5;i++){const b=await p.export({slide:p.slides.items[i],format:'png',scale:1});await fs.writeFile(path.join(work,`preview/slide-${i+1}.png`),new Uint8Array(await b.arrayBuffer()));}
const result=await finalizePresentation({workspaceDir:work,candidatePath:candidate,finalPath:path.join(work,'output/CYBERMIND_demo.pptx'),pythonExecutable:'C:/Users/as030/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit'],explicitTotalSlideCount:5,fontPolicy:{basis:'design',families:[font]},verifyArtifactToolImport:true,receiptPath:path.join(work,'build/validation.json')});console.log(JSON.stringify(result));

