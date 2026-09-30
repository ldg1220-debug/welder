// 실행: node tests/engine.test.mjs   (welder-cert.html 안의 ENGINE 블록을 그대로 꺼내 검증)
import fs from 'node:fs'; import assert from 'node:assert/strict';
const html = fs.readFileSync(new URL('../welder-cert.html', import.meta.url), 'utf8');
const src = html.split('/*ENGINE-START*/')[1].split('/*ENGINE-END*/')[0];
const E = new Function(src + '; return {calcExpire,validityText,monthsBetween,certAlert,judge,calculateRangeOfApproval,designation};')();
const R = (o) => Object.fromEntries(E.calculateRangeOfApproval({process:'135 MAG',productType:'P',joint:'BW',fillerGroup:'FM 1',fillerType:'S',backing:'ss nb',position:'PC',weldingDate:'2024-08-21',transfer:'globular/spray',gas:'M21',thickness:12,...o}).items.map(x=>[x.key,x.range]));
let n=0; const t=(name,fn)=>{fn(); n++; console.log('ok -',name);};

t('유효기간 = 용접일+3년-1일 (샘플 인증서)',()=>assert.equal(E.calcExpire('2024-08-21'),'2027-08-20'));
t('윤일 2/29',()=>assert.equal(E.calcExpire('2024-02-29'),'2027-02-27'));
t('유효기간 문구',()=>assert.equal(E.validityText('2024-08-21','2027-08-20'),'2024-08-21 ~ 2027-08-20 (refer to 9.3 a)'));
t('샘플: BW 135 t12 PC → 두께 ≥3, PA·PC, FM1·FM2, S·M',()=>{const r=R({});
  assert.equal(r.thickness,'≥ 3'); assert.equal(r.deposited,'≥ 3'); assert.equal(r.position,'PA, PC');
  assert.equal(r.fillerGroup,'FM1, FM2'); assert.equal(r.fillerType,'S, M'); assert.equal(r.backing,'ss nb, ss mb, bs'); assert.equal(r.transfer,'Globular or Spray');
  assert.match(r.product,/^P, T/);});
t('t=2.3 → 2.3 ≤ t ≤ 4.6',()=>assert.equal(R({thickness:2.3,deposited:2.3}).thickness,'2.3 ≤ t ≤ 4.6'));
t('t=6 → 3 ≤ t ≤ 12',()=>assert.equal(R({thickness:6,deposited:6}).thickness,'3 ≤ t ≤ 12'));
t('t=3 → 3 ≤ t ≤ 6',()=>assert.equal(R({thickness:3,deposited:3}).thickness,'3 ≤ t ≤ 6'));
t('t=11.9 → 3 ≤ t ≤ 23.8',()=>assert.equal(R({thickness:11.9,deposited:11.9}).thickness,'3 ≤ t ≤ 23.8'));
t('FW t=3 → ≥3, PF → PA,PB,PF',()=>{const r=R({joint:'FW',thickness:3,position:'PF'});assert.equal(r.thickness,'≥ 3');assert.equal(r.position,'PA, PB, PF');});
t('미지원 자세/FM → 수동검토',()=>{
  assert.equal(E.calculateRangeOfApproval({process:'135 MAG',joint:'BW',thickness:6,position:'H-L045',fillerGroup:'FM1'}).manual_review_required,true);
  assert.equal(E.calculateRangeOfApproval({process:'135 MAG',joint:'BW',thickness:6,position:'PC',fillerGroup:'FM5'}).manual_review_required,true);});
t('311 가스용접 → 수동검토',()=>assert.equal(E.calculateRangeOfApproval({process:'311',joint:'BW',thickness:6,position:'PC',fillerGroup:'FM1'}).manual_review_required,true));
t('파이프 D=50 → D ≥ 25',()=>assert.equal(R({productType:'T',pipeDiameter:50}).diameter,'D ≥ 25'));
t('파이프 D=20 → 20 ≤ D ≤ 40',()=>assert.equal(R({productType:'T',pipeDiameter:20}).diameter,'20 ≤ D ≤ 40'));
t('미지원 규격 → 수동검토',()=>assert.equal(E.calculateRangeOfApproval({},'ASME IX').manual_review_required,true));
t('Designation (샘플)',()=>assert.equal(E.designation({process:'135 MAG',productType:'P',joint:'BW',fillerGroup:'FM 1',fillerType:'S',thickness:12,position:'PC',backing:'ss nb'}),'EN ISO 9606-1 135 P BW FM1 S t12 PC ss nb'));
t('판정: 샘플(VT+RT만)은 ISO 기준 합격, 사내 엄격 기준은 진행중',()=>{
  assert.equal(E.judge('BW',{vt:'pass',rtut:'pass'},false),'pass'); assert.equal(E.judge('BW',{vt:'pass',rtut:'pass'},true),'pending');});
t('판정: 굽힘만으로도 합격(ISO), Fail이 하나라도 있으면 불합격',()=>{
  assert.equal(E.judge('BW',{vt:'pass',bend:'pass'},false),'pass'); assert.equal(E.judge('BW',{vt:'pass',rtut:'pass',bend:'fail'},false),'fail');
  assert.equal(E.judge('BW',{rtut:'pass',bend:'pass'},false),'pending');});
t('판정: FW = VT+Macro',()=>{assert.equal(E.judge('FW',{vt:'pass',macro:'pass'},false),'pass');assert.equal(E.judge('FW',{vt:'pass'},false),'pending');assert.equal(E.judge('FW',{vt:'fail',macro:'pass'},true),'fail');});
t('개월 수·경고',()=>{
  assert.equal(E.monthsBetween('2024-08-21','2025-02-20'),5); assert.equal(E.monthsBetween('2024-08-21','2025-02-21'),6); assert.equal(E.monthsBetween('2024-01-31','2024-02-29'),1);
  assert.equal(E.certAlert('2024-08-21','2027-08-20',0,'2025-02-21'),null); assert.equal(E.certAlert('2024-08-21','2027-08-20',0,'2025-03-21'),'renewal');
  assert.equal(E.certAlert('2024-08-21','2027-08-20',1,'2025-03-21'),null); assert.equal(E.certAlert('2024-08-21','2027-08-20',5,'2027-08-21'),'expired');});
console.log(`\n${n} passed`);
