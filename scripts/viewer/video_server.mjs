/** ログ動画専用のloopback配信。既存ViewerのVite依存だけを使う。 */
import {readFileSync,writeFileSync} from 'node:fs';
import {resolve,dirname,join} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..');
const app=join(root,'apps/mujoco-viewer');
const [bundle,receipt]=process.argv.slice(2);
if(!bundle||!receipt) throw new Error('bundle and receipt paths required');
const {createServer}=await import(pathToFileURL(join(app,'node_modules/vite/dist/node/index.js')));
const server=await createServer({configFile:false,root:app,publicDir:join(bundle,'public'),cacheDir:join(bundle,'.vite'),
  resolve:{alias:[{find:'@mujoco/mujoco/mujoco.wasm',replacement:join(app,'node_modules/@mujoco/mujoco/mujoco.wasm')}]},
  optimizeDeps:{exclude:['@mujoco/mujoco']},
  server:{host:'127.0.0.1',port:0,strictPort:false,fs:{allow:[app,bundle,root]}}});
try {
  await server.listen();
  const address=server.httpServer.address();
  writeFileSync(receipt,JSON.stringify({url:`http://127.0.0.1:${address.port}/raw-video.html`}),{flag:'wx'});
  let closing=false;
  const close=async()=>{if(closing)return;closing=true;await server.close();process.exit(0);};
  process.stdin.resume();process.stdin.on('data',close);process.stdin.on('end',close);
  process.on('SIGTERM',close);process.on('SIGINT',close);
} catch(error) {await server.close();throw error;}
