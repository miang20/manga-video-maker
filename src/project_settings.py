import json
from pathlib import Path
DEFAULTS={'voice_source':'upload','voice':'af_heart','voice_speed':1.0,'style':'bw_manga','motion_intensity':'normal','music':None}
VALID={'voice_source':{'upload','kokoro'},'style':{'bw_manga','color','clean'},'motion_intensity':{'subtle','normal','strong'},'music':{'on','off',None}}
def resolve_project_settings(project: Path, overrides=None):
    settings=dict(DEFAULTS)
    path=Path(project)/'project.json'
    if path.is_file():
        loaded=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(loaded,dict): raise ValueError('project.json must contain a JSON object.')
        settings.update({k:v for k,v in loaded.items() if k in DEFAULTS and v is not None})
    for key,value in (overrides or {}).items():
        if key in DEFAULTS and value is not None and value!='project': settings[key]=value
    for key,choices in VALID.items():
        if settings.get(key) not in choices: raise ValueError('Invalid project setting %s=%r'%(key,settings.get(key)))
    try: settings['voice_speed']=max(0.7,min(1.3,float(settings['voice_speed'])))
    except (TypeError,ValueError): raise ValueError('voice_speed must be between 0.7 and 1.3.')
    return settings
