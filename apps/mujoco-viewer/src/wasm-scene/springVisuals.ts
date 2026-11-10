/** 一自由度ばねの表示部品。native姿勢だけを読み、接触形状や物理状態を変更しない。 */
import {BoxGeometry, BufferAttribute, BufferGeometry, Group, Mesh, MeshPhongMaterial, Uint32BufferAttribute} from "three";
import type {DisplayBounds} from "./sceneFraming.js";

export interface SpringModel {
  njnt: number; ngeom: number;
  jnt_type: ArrayLike<number>; jnt_bodyid: ArrayLike<number>; jnt_qposadr: ArrayLike<number>;
  jnt_range: ArrayLike<number>; qpos_spring: ArrayLike<number>;
  body_parentid: ArrayLike<number>; body_jntnum: ArrayLike<number>;
  geom_type: ArrayLike<number>; geom_bodyid: ArrayLike<number>; geom_size: ArrayLike<number>;
}
export interface SpringData {
  qpos: ArrayLike<number>; xaxis: ArrayLike<number>;
  geom_xpos: ArrayLike<number>; geom_xmat: ArrayLike<number>;
}
export interface SpringBinding {
  id: string; joint: number; address: number; geom: number; reference: number;
  half: readonly number[]; restLength: number; radius: number; wire: number;
}

/** Environmentの明示spring命名・slide・world固定基部・boxを確認し、推測で一般jointへ付けない。 */
export function springBindings(model: SpringModel, jointName: (id: number) => string): SpringBinding[] {
  const result: SpringBinding[] = [];
  for (let joint=0; joint<model.njnt; joint++) {
    const match=/^object__([a-z][a-z0-9_]{0,47})__spring$/.exec(jointName(joint));
    if (!match) continue;
    const body=Number(model.jnt_bodyid[joint]), address=Number(model.jnt_qposadr[joint]);
    if (model.jnt_type[joint]!==2 || model.body_parentid[body]!==0 || model.body_jntnum[body]!==1) continue;
    const geoms=Array.from({length:model.ngeom},(_,i)=>i).filter(i=>model.geom_bodyid[i]===body);
    if (geoms.length!==1 || model.geom_type[geoms[0]]!==6) continue;
    const geom=geoms[0], half=Array.from({length:3},(_,i)=>Number(model.geom_size[3*geom+i]));
    const hi=Number(model.jnt_range[2*joint+1]), reference=Number(model.qpos_spring[address]);
    if (!Number.isInteger(address) || address<0 || model.jnt_range[2*joint]!==0
      || !Number.isFinite(hi) || hi<=0 || !Number.isFinite(reference)
      || reference<0 || reference>=hi || half.some(v=>!Number.isFinite(v)||v<=0)) continue;
    const size=Math.min(...half);
    result.push({id:match[1],joint,address,geom,reference,half,
      restLength:Math.max(1.8*(hi-reference),size*1.6),radius:size*.45,wire:size*.05});
  }
  return result;
}

/** 正の変位だけコイルを短縮する。下限・上限超過を正常値へclampしない。 */
export function springPose(binding: SpringBinding, data: SpringData) {
  const q=Number(data.qpos[binding.address]);
  const axis=Array.from({length:3},(_,i)=>Number(data.xaxis[3*binding.joint+i]));
  const center=Array.from({length:3},(_,i)=>Number(data.geom_xpos[3*binding.geom+i]));
  const rotation=Array.from({length:9},(_,i)=>Number(data.geom_xmat[9*binding.geom+i]));
  if (![q,...axis,...center,...rotation].every(Number.isFinite) || Math.abs(Math.hypot(...axis)-1)>1e-6) return null;
  const depth=binding.half.reduce((sum,half,i)=>sum+half*Math.abs(axis[0]*rotation[i]+axis[1]*rotation[3+i]+axis[2]*rotation[6+i]),0);
  const start=center.map((v,i)=>v+axis[i]*depth);
  const length=binding.restLength-(q-binding.reference);
  const anchor=start.map((v,i)=>v+axis[i]*length);
  return {q,axis,start,anchor,length};
}

/** 頂点bufferを一度だけ確保。長さ変更でwireの太さを縮めず、meshを再生成しない。 */
export class SpringCoil {
  readonly geometry=new BufferGeometry();
  readonly positions=new Float32Array(141*9*3);
  readonly normals=new Float32Array(141*9*3);
  private readonly positionAttribute=new BufferAttribute(this.positions,3);
  private readonly normalAttribute=new BufferAttribute(this.normals,3);
  private lastLength=NaN;
  constructor(readonly radius:number,readonly wire:number) {
    const indices:number[]=[];
    for(let i=0;i<140;i++) for(let j=0;j<8;j++) {
      const a=i*9+j,b=a+9; indices.push(a,a+1,b,b,a+1,b+1);
    }
    this.geometry.setAttribute("position",this.positionAttribute);
    this.geometry.setAttribute("normal",this.normalAttribute);
    this.geometry.setIndex(new Uint32BufferAttribute(indices,1));
  }
  update(length:number):void {
    if(length===this.lastLength) return;
    if(!Number.isFinite(length)||length<=0) throw new Error("positive visual spring length required");
    const pitch=2*Math.PI*7*this.radius, norm=Math.hypot(pitch,length);
    for(let i=0;i<=140;i++) {
      const t=i/140,a=2*Math.PI*7*t,c=Math.cos(a),s=Math.sin(a);
      for(let j=0;j<=8;j++) {
        const b=2*Math.PI*j/8,cb=Math.cos(b),sb=Math.sin(b),k=(i*9+j)*3;
        const nx=c*cb-length*s/norm*sb,ny=s*cb+length*c/norm*sb,nz=-pitch/norm*sb;
        this.positions[k]=this.radius*c+this.wire*nx;
        this.positions[k+1]=this.radius*s+this.wire*ny;
        this.positions[k+2]=length*t+this.wire*nz;
        this.normals[k]=nx;this.normals[k+1]=ny;this.normals[k+2]=nz;
      }
    }
    this.positionAttribute.needsUpdate=true;this.normalAttribute.needsUpdate=true;
    this.geometry.computeBoundingBox();this.geometry.computeBoundingSphere();this.lastLength=length;
  }
  dispose():void { this.geometry.dispose(); }
}

interface Visual {
  binding:SpringBinding; group:Group; coil:SpringCoil; mesh:Mesh; moving:Mesh; fixed:Mesh;
  post:Mesh; foot:Mesh; bounds:DisplayBounds|null;
}

/** model寿命のowner。非ばねsceneへの切替とdisposeでGPU資源を一度だけ解放する。 */
export class SpringVisuals {
  readonly group=new Group();
  private entries:Visual[]=[];
  private materials:MeshPhongMaterial[]=[];
  private floor=-1;
  constructor() { this.group.name="linear spring visual assembly (non-colliding)"; }
  get count():number { return this.entries.length; }
  get bounds():DisplayBounds|null {
    const values=this.entries.filter(v=>v.group.visible&&v.bounds!==null).map(v=>v.bounds!);
    return values.length===0?null:{min:[0,1,2].map(i=>Math.min(...values.map(v=>v.min[i]))) as [number,number,number],
      max:[0,1,2].map(i=>Math.max(...values.map(v=>v.max[i]))) as [number,number,number]};
  }
  configure(model:SpringModel,jointName:(id:number)=>string):void {
    this.clear();
    const bindings=springBindings(model,jointName);
    if(bindings.length===0) return;
    this.floor=Array.from({length:model.ngeom},(_,i)=>i).find(i=>model.geom_type[i]===0&&model.geom_bodyid[i]===0)??-1;
    const metal=new MeshPhongMaterial({color:0xd4e1ed,shininess:80,specular:0x899ab4});
    const fixedMaterial=new MeshPhongMaterial({color:0x64748b,shininess:30});
    this.materials=[metal,fixedMaterial];
    for(const binding of bindings) {
      const group=new Group();group.name=`spring:${binding.id}`;group.visible=false;this.group.add(group);
      const coil=new SpringCoil(binding.radius,binding.wire),mesh=new Mesh(coil.geometry,metal);
      const width=2*Math.max(...binding.half);
      const moving=new Mesh(new BoxGeometry(width*.75,width*.75,binding.wire*1.6),metal);
      const fixed=new Mesh(new BoxGeometry(width*1.25,width*1.25,binding.wire*4),fixedMaterial);
      group.add(mesh,moving,fixed);
      const post=new Mesh(new BoxGeometry(1,1,1),fixedMaterial),foot=new Mesh(new BoxGeometry(1,1,1),fixedMaterial);
      post.visible=foot.visible=false;this.group.add(post,foot);
      this.entries.push({binding,group,coil,mesh,moving,fixed,post,foot,bounds:null});
    }
  }
  update(data:SpringData):void {
    for(const entry of this.entries) {
      const {binding,group,coil,mesh,moving,fixed,post,foot}=entry;
      const pose=springPose(binding,data);group.visible=pose!==null;post.visible=foot.visible=false;entry.bounds=null;
      if(!pose) continue;
      const {axis,start,anchor,length}=pose;
      group.position.set(start[0],start[1],start[2]);
      // z軸からnative world軸への純粋な表示回転。RobotのFKは再実装しない。
      if(axis[2]<-1+1e-12) group.quaternion.set(1,0,0,0);
      else {const s=Math.sqrt(2*(1+axis[2]));group.quaternion.set(-axis[1]/s,axis[0]/s,0,s/2);}
      mesh.visible=length>binding.wire*2;
      if(mesh.visible) coil.update(length);
      moving.position.set(0,0,0);fixed.position.set(0,0,length);
      const width=2*Math.max(...binding.half),pad=width*.9;
      entry.bounds={min:[0,1,2].map(i=>Math.min(start[i],anchor[i])-pad) as [number,number,number],
        max:[0,1,2].map(i=>Math.max(start[i],anchor[i])+pad) as [number,number,number]};
      // 水平のworld支持面が宣言されている場合だけ、固定端の支持柱を表示する。
      const floorZ=this.floor<0?NaN:Number(data.geom_xpos[this.floor*3+2]);
      const horizontal=this.floor>=0&&Math.abs(Number(data.geom_xmat[this.floor*9+8])-1)<1e-6;
      const height=anchor[2]-width*.625-floorZ;
      if(horizontal&&Number.isFinite(height)&&height>binding.wire*4&&Math.abs(axis[2])<1e-6) {
        post.visible=foot.visible=true;
        post.position.set(anchor[0],anchor[1],floorZ+height/2);post.scale.set(width*.18,width*.18,height);
        foot.position.set(anchor[0],anchor[1],floorZ+binding.wire*2);foot.scale.set(width*1.6,width*1.6,binding.wire*4);
        entry.bounds.min[2]=Math.min(entry.bounds.min[2],floorZ);
      }
    }
  }
  clear():void {
    for(const entry of this.entries) {
      entry.coil.dispose();
      for(const mesh of [entry.moving,entry.fixed,entry.post,entry.foot]) mesh.geometry.dispose();
    }
    for(const material of this.materials) material.dispose();
    this.entries=[];this.materials=[];this.floor=-1;this.group.clear();
  }
}
