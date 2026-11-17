"""Real upload calculator on one explicitly offline HAIDA fixture; no Java business writes."""
import json
import shutil
import subprocess
import sys
import uuid
from river_yolo import ROOT, fingerprint, write_json


def main():
    identity=str(uuid.uuid4());output=ROOT/'runs/vision'/identity;output.mkdir(parents=True)
    source=sorted((ROOT/'data/haida-yolo/images/test').glob('*.jpg'))[0]
    shutil.copyfile(source,output/'input.image')
    config=json.loads((ROOT/'weights/patrol/model.json').read_text(encoding='utf-8'))
    result=subprocess.run([sys.executable,str(ROOT/'scripts/vision_upload.py'),'--id',identity,
        '--model-sha',config['modelSha256'],'--image-sha',fingerprint(output/'input.image')],capture_output=True,timeout=130)
    report={'passed':False,'real_model':True,'source':'HAIDA test offline fixture; not Hangzhou live image','business_writes':0,'analysis_id':identity}
    if result.returncode==0:
        value=json.loads((output/'result.json').read_text(encoding='utf-8'))
        report.update(passed=value['imageSha256']==fingerprint(source) and value['modelSha256']==config['modelSha256'],
            detection_count=len(value['predictions']),device=value['device'])
    else:report['error']='Calculator failed; private runtime logs not printed'
    write_json(ROOT.parent/'docs/verification/vision-upload-model.json',report)
    print(json.dumps(report,ensure_ascii=False,indent=2));return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
