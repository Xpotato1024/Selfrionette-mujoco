import assert from "node:assert/strict";
import {describe,it} from "node:test";
import loadMujoco from "@mujoco/mujoco";
import {springBindings,springPose,SpringCoil,SpringVisuals} from "../src/wasm-scene/springVisuals.js";
import {applyMujocoDisplayPose} from "../src/wasm-scene/mujocoDisplayPose.js";
const api=await loadMujoco();
const xml=(name="object__cube__spring",quat="1 0 0 0",floor=true,ref=0)=>`<mujoco><compiler angle="radian"/><worldbody>
${floor?'<geom type="plane" size="1 1 .1"/>':''}<body pos=".24 -.36 .28" quat="${quat}">
<joint name="${name}" type="slide" axis="0 -1 0" range="0 .05" limited="true" springref="${ref}" stiffness="100" damping="2"/>
<geom type="box" size=".05 .05 .05" mass=".2"/></body></worldbody></mujoco>`;
function withModel(run:(model:any,data:any,name:(id:number)=>string)=>void,document=xml()) {
  const model=api.MjModel.from_xml_string(document),data=new api.MjData(model);
  try {run(model,data,id=>String(api.mj_id2name(model,api.mjtObj.mjOBJ_JOINT.value,id)??""));}
  finally {data.delete();model.delete();}
}
const close=(actual:number,expected:number)=>assert.ok(Math.abs(actual-expected)<1e-9,`${actual} != ${expected}`);

describe("一自由度ばねのnative状態による描画",()=>{
  it("実WASMのslideから可動端を取得し、固定端を保持してqだけ短縮する",()=>withModel((model,data,name)=>{
    const bindings=springBindings(model,name);assert.equal(bindings.length,1);
    const b=bindings[0];close(b.restLength,.09);
    applyMujocoDisplayPose(api,model,data,[0]);const initial=springPose(b,data)!;
    for(const q of [.02,.02,.04,0]) {
      applyMujocoDisplayPose(api,model,data,[q]);const pose=springPose(b,data)!;
      close(initial.length-pose.length,q);
      pose.anchor.forEach((v,i)=>close(v,initial.anchor[i]));
      close(pose.start[1],-.41-q);assert.equal(data.time,0);
    }
  }));
  it("worldへ回転した対象でもnative軸へ追従する",()=>withModel((model,data,name)=>{
    const b=springBindings(model,name)[0];
    applyMujocoDisplayPose(api,model,data,[0]);const before=springPose(b,data)!;
    applyMujocoDisplayPose(api,model,data,[.03]);const after=springPose(b,data)!;
    close(after.axis[0],1);close(after.start[0]-before.start[0],.03);
    after.anchor.forEach((v,i)=>close(v,before.anchor[i]));
  },xml("object__rotated__spring","0.7071067811865476 0 0 0.7071067811865476")));
  it("初期表示値でなくnative springrefを基準にする",()=>withModel((model,data,name)=>{
    const b=springBindings(model,name)[0];
    applyMujocoDisplayPose(api,model,data,[.01]);const before=springPose(b,data)!;
    applyMujocoDisplayPose(api,model,data,[.03]);const after=springPose(b,data)!;
    close(before.length,b.restLength);close(before.length-after.length,.02);
    after.anchor.forEach((v,i)=>close(v,before.anchor[i]));
  },xml("object__offset__spring","1 0 0 0",true,.01)));
  it("soft limit超過を表示側でclampしない",()=>withModel((model,data,name)=>{
    const b=springBindings(model,name)[0];
    for(const q of [-.002,.055]) {
      applyMujocoDisplayPose(api,model,data,[q]);const pose=springPose(b,data)!;
      close(pose.q,q);close(pose.length,b.restLength-q);
    }
  }));
  it("通常jointと非対応形状へばねを推測追加しない",()=>{
    for(const document of [xml("robot_joint"),xml().replace('type="box"','type="sphere"'),xml().replace('type="slide"','type="hinge"')])
      withModel((model,_data,name)=>assert.equal(springBindings(model,name).length,0),document);
  });
  it("modelとqpos/時間を変更せずboundedなgeometryを再利用する",()=>withModel((model,data,name)=>{
    const visual=new SpringVisuals();visual.configure(model,name);assert.equal(visual.count,1);
    const params=[...model.geom_size,...model.jnt_range,...model.qpos_spring];
    const objects=[...visual.group.children];const geometries:any[]=[];
    visual.group.traverse(o=>{if((o as any).geometry)geometries.push((o as any).geometry);});
    for(let i=0;i<400;i++) {
      const q=.025+.02*Math.sin(i/10);applyMujocoDisplayPose(api,model,data,[q]);
      const before=[...data.qpos,...data.qvel,data.time];visual.update(data);
      assert.deepEqual([...data.qpos,...data.qvel,data.time],before);
      assert.deepEqual([...visual.group.children],objects);
    }
    assert.deepEqual([...model.geom_size,...model.jnt_range,...model.qpos_spring],params);
    const after:any[]=[];visual.group.traverse(o=>{if((o as any).geometry)after.push((o as any).geometry);});
    assert.deepEqual(after,geometries);assert.equal(geometries.length,5);
    assert.ok(visual.bounds);close(visual.bounds!.min[2],0);visual.clear();
  }));
  it("床なしworldへ支持柱・床を捏造しない",()=>withModel((model,data,name)=>{
    const visual=new SpringVisuals();visual.configure(model,name);applyMujocoDisplayPose(api,model,data,[.02]);visual.update(data);
    assert.equal(visual.group.children[1].visible,false);assert.equal(visual.group.children[2].visible,false);
    assert.ok(visual.bounds!.min[2]>0);visual.clear();
  },xml("object__cube__spring","1 0 0 0",false)));
  it("NaNまたは潰れた長さで古いコイルを正常表示しない",()=>withModel((model,data,name)=>{
    const visual=new SpringVisuals();visual.configure(model,name);applyMujocoDisplayPose(api,model,data,[0]);visual.update(data);
    data.qpos[0]=NaN;visual.update(data);assert.equal(visual.group.children[0].visible,false);assert.equal(visual.bounds,null);
    applyMujocoDisplayPose(api,model,data,[.15]);visual.update(data);
    assert.equal(visual.group.children[0].children[0].visible,false);close(data.qpos[0],.15);visual.clear();
  }));
  it("scene切替・二重clearでGPU資源を一度だけ破棄する",()=>withModel((model,data,name)=>{
    const visual=new SpringVisuals();visual.configure(model,name);
    const geometries=new Set<any>(),materials=new Set<any>();
    visual.group.traverse(o=>{const m=o as any;if(m.geometry)geometries.add(m.geometry);if(m.material)materials.add(m.material);});
    const disposed=new Map<any,number>();
    for(const asset of [...geometries,...materials])asset.addEventListener("dispose",()=>disposed.set(asset,(disposed.get(asset)??0)+1));
    visual.configure(model,()=>"unrelated");visual.clear();
    assert.equal(visual.count,0);assert.equal(visual.group.children.length,0);
    assert.equal(disposed.size,geometries.size+materials.size);assert.ok([...disposed.values()].every(v=>v===1));
  }));
  it("複数ばねを個別に追従させる",()=>withModel((model,data,name)=>{
    const visual=new SpringVisuals();visual.configure(model,name);assert.equal(visual.count,2);
    applyMujocoDisplayPose(api,model,data,[.01,.03]);visual.update(data);
    const groups=visual.group.children.filter(g=>g.name.startsWith("spring:"));assert.equal(groups.length,2);
    assert.notEqual(groups[0].position.y,groups[1].position.y);visual.clear();
  },xml().replace('</worldbody>','<body pos=".5 -.36 .28"><joint name="object__other__spring" type="slide" axis="0 -1 0" range="0 .05" limited="true"/><geom type="box" size=".05 .05 .05" mass=".2"/></body></worldbody>')));
});

describe("コイルのbuffer",()=>{
  it("再割当せず更新し、同じ長さではbuffer versionを増やさない",()=>{
    const coil=new SpringCoil(.024,.0025),geometry=coil.geometry,positions=coil.positions;
    coil.update(.09);const normal=coil.normals.slice(),before=positions.slice();
    const ids=Array.from((geometry as any).index.array.slice(0,3)) as number[];
    const points=ids.map(id=>Array.from(positions.slice(id*3,id*3+3)));
    const u=points[1].map((v,i)=>v-points[0][i]),v=points[2].map((x,i)=>x-points[0][i]);
    const cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];
    assert.ok(cross.reduce((sum,x,i)=>sum+x*coil.normals[ids[0]*3+i],0)>0,"outward triangle winding");
    const attribute=(geometry as any).getAttribute("position"),version=attribute.version;
    coil.update(.09);assert.equal(attribute.version,version);
    coil.update(.04);assert.equal(coil.geometry,geometry);assert.equal(coil.positions,positions);assert.notDeepEqual(positions,before);
    assert.notDeepEqual(coil.normals,normal);assert.ok([...positions].every(Number.isFinite));
    for(let i=0;i<coil.normals.length;i+=3)assert.ok(Math.abs(Math.hypot(...coil.normals.slice(i,i+3))-1)<1e-6);
    assert.throws(()=>coil.update(0));assert.throws(()=>coil.update(NaN));coil.dispose();
  });
});

describe("可動板のコイル径",()=>{
  it("板厚ではなくばね軸に直交する面幅で径を決め、物理板へ表示板を重ねない",()=>{
    withModel((model,data,name)=>{
      const b=springBindings(model,name)[0];close(b.radius,.0225);close(b.wire,.0025);
      const visual=new SpringVisuals();visual.configure(model,name);
      applyMujocoDisplayPose(api,model,data,[.02]);visual.update(data);
      assert.equal(visual.group.children[0].children[1].visible,false);
      close(springPose(b,data)!.depth,.005);visual.clear();
    },xml().replace('size=".05 .05 .05"','size=".05 .005 .05"'));
  });
  it("geomを回転した薄板もnative局所軸と整合する",()=>{
    withModel((model,data,name)=>{
      const b=springBindings(model,name)[0];close(b.radius,.0225);
      applyMujocoDisplayPose(api,model,data,[0]);close(springPose(b,data)!.depth,.005);
    },xml().replace('size=".05 .05 .05"','size=".005 .05 .05" quat="0.7071067811865476 0 0 0.7071067811865476"'));
  });
});
