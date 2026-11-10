/** 検証済み記録を単一canvasへ投影する。装飾DOM、入力送信、physics stepは持たない。 */
import {createMujocoSceneRenderer} from "./mujocoSceneRenderer.js";
import type {TransportPayloadV0} from "../types/transportPayload.js";
import type {CameraView} from "./cameraPresentation.js";
export async function startOfflineVideo() {
  const response=await fetch("/replay.json");
  if(!response.ok) throw new Error("recorded state bundle unavailable");
  const dataset=await response.json();
  if(dataset.schema!=="raw-video-bundle/v1" || !Array.isArray(dataset.frames) || dataset.frames.length===0)
    throw new Error("invalid raw video bundle");
  const cameras:CameraView[]=["operator","iso","front","side","top"];
  if(!cameras.includes(dataset.camera)) throw new Error("unknown camera preset");
  let state:any=null;
  const view=createMujocoSceneRenderer({canvas:document.querySelector("canvas")!,profile:null,
    websocketUrl:null,offline:true,overlays:false,initialCameraView:dataset.camera,
    onStateChange:s=>{state=s;}});
  try {
    await view.prepareWorkbench(dataset.initial,dataset.epoch);
    const show=(index:number)=>{
      if(!Number.isInteger(index)||index<0||index>=dataset.frames.length) throw new Error("frame index out of bounds");
      const saved=dataset.frames[index];
      const payload:TransportPayloadV0={...dataset.initial,frame_index:saved.tick,time_s:saved.time_s,
        qpos:saved.qpos,qvel:saved.qvel,bodies:[],sites:[]};
      view.applyOfflinePayload(payload);
      if(state?.qposStatus!=="ready") throw new Error(state?.qposError??"recorded pose rejected");
      view.renderFrame();
      return {tick:saved.tick,time_s:saved.time_s,rendered:view.counters().renderedFrameIndex};
    };
    show(0);
    return {show,counters:()=>view.counters(),close:()=>view.dispose()};
  } catch(error) {view.dispose();throw error;}
}
if(typeof window!=="undefined") {
  startOfflineVideo().then(api=>{(window as any).rawVideo=api;})
    .catch(error=>{(window as any).rawVideoError=String(error);});
}
