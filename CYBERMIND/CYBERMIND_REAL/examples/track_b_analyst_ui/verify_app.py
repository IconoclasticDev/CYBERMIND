"""Run real Streamlit flows against reviewed epoch 185 without a GPU."""
import os, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
os.environ['CYBERMIND_CHECKPOINT'] = str(ROOT/'examples/phase3_third_round/extended200/checkpoints/combined.pt')
os.environ['OMP_NUM_THREADS'] = '2'
sys.path.insert(0,str(ROOT/'src'))
from streamlit.testing.v1 import AppTest
from cybermind.analyst.view import load_case
app = AppTest.from_file(str(ROOT/'scripts/app.py'), default_timeout=120).run()
assert not app.exception, app.exception
assert len(app.dataframe) == 1
assert len(app.dataframe[0].value) == 5
# AppTest widget values are underlying host indices, not display strings.
app.multiselect[0].set_value([0]).run()
next(button for button in app.button if button.label == 'Run isolation simulations').click().run()
assert not app.exception, app.exception
assert len(app.session_state['interventions']) == 2
next(button for button in app.button if button.label == 'Compute model explanation').click().run()
assert not app.exception, app.exception
assert app.session_state['explanation']['gradient_x_input']
rows = app.dataframe[0].value.to_dict(orient='records')
case = {'forecast':rows, 'interventions':app.session_state['interventions'],
        'explanation':app.session_state['explanation']}
_, _, _, lineage, count = load_case(os.environ['CYBERMIND_CHECKPOINT'],ROOT,0)
case['lineage'] = lineage
assert lineage['checkpoint_epoch'] == 185
# Changing the sequence must invalidate previous host effects/explanations.
app.number_input[0].set_value(1).run()
assert not app.exception, app.exception
assert app.session_state['interventions'] == []
assert app.session_state['explanation'] is None
app.sidebar.text_input[0].set_value(str(ROOT/'nonexistent_checkpoint.pt')).run()
assert not app.exception and app.info
result = {'passed':True, 'checkpoint_epoch':185, 'test_sequences':count,
          'runtime':'Streamlit AppTest, actual CPU inference',
          'checks':['real checkpoint load','five rows: now plus four futures','isolation comparison',
                    'feature and temporal explanation','case switch invalidates derived results',
                    'missing checkpoint guidance','JSON case export payload'], 'case':case}
Path(__file__).with_name('verification.json').write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k != 'case'},indent=2))
