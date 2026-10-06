#!/usr/bin/env node
// sealed-exam-blockA exam copy: see join/make_join.py and the .diff beside this file
// decimals.js — ERC-20 decimals() (and symbol() for quote currencies) for every token and quote currency that has a v4 swap
// in the shards, via Multicall3.aggregate3 on the public RPC (research lane, paced). Read-only on chain; writes decimals.json here.
// Usage: node decimals.js <addr_quotes.json> <addr_toks.json>
'use strict';
require('dns').setDefaultResultOrder('ipv4first');     // the box has no v6 egress (f-nodefetc)
const fs = require('fs'), path = require('path');
const { ethers } = require('/home/green/noxabot/node_modules/ethers');
const RPC = process.env.RPC || 'https://robinhood-rpc.publicnode.com';
const MC = '0xcA11bde05977b3631167028862bE2a173976CA11';
const iface = new ethers.utils.Interface(['function aggregate3((address target, bool allowFailure, bytes callData)[] calls) view returns ((bool success, bytes returnData)[])']);
const DEC = '0x313ce567', SYM = '0x95d89b41';
const OUT = path.join('/home/green/projects/patches/sealed-exam-blockA/work/v4join', 'decimals.json');
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function ethCall(data) {
  for (let a = 0; a < 6; a++) {
    try {
      const r = await fetch(RPC, { method: 'POST', headers: { 'Content-Type': 'application/json' }, signal: AbortSignal.timeout(60000),
        body: JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'eth_call', params: [{ to: MC, data }, 'latest'] }) }).then(x => x.json());
      if (r.result) return r.result;
      throw new Error(JSON.stringify(r.error || r).slice(0, 200));
    } catch (e) { await sleep(3000 * (a + 1)); if (a === 5) throw e; }
  }
}
function decodeStr(hex) {
  try { return ethers.utils.defaultAbiCoder.decode(['string'], hex)[0].slice(0, 24); } catch {}
  try { return ethers.utils.parseBytes32String(hex.slice(0, 66)); } catch { return null; }
}
(async () => {
  const [qf, tf] = process.argv.slice(2);
  const quotes = JSON.parse(fs.readFileSync(qf, 'utf8')).map(x => x[0]);
  const toks = JSON.parse(fs.readFileSync(tf, 'utf8')).map(x => x[0]);
  const out = fs.existsSync(OUT) ? JSON.parse(fs.readFileSync(OUT, 'utf8')) : { dec: {}, sym: {} };
  out.dec['0x0000000000000000000000000000000000000000'] = 18; out.sym['0x0000000000000000000000000000000000000000'] = 'ETH';
  const jobs = [];
  for (const a of quotes) { if (a !== '0x0000000000000000000000000000000000000000') { if (!(a in out.dec)) jobs.push([a, DEC]); if (!(a in out.sym)) jobs.push([a, SYM]); } }
  for (const a of toks) if (!(a in out.dec) && a !== '0x0000000000000000000000000000000000000000') jobs.push([a, DEC]);
  console.log('jobs', jobs.length);
  const B = 400;
  for (let i = 0; i < jobs.length; i += B) {
    const chunk = jobs.slice(i, i + B);
    const data = iface.encodeFunctionData('aggregate3', [chunk.map(([a, s]) => ({ target: a, allowFailure: true, callData: s }))]);
    const res = iface.decodeFunctionResult('aggregate3', await ethCall(data))[0];
    chunk.forEach(([a, s], k) => {
      const { success, returnData } = res[k];
      if (s === DEC) out.dec[a] = success && returnData.length >= 66 ? ethers.BigNumber.from(returnData.slice(0, 66)).toNumber() : null;
      else out.sym[a] = success ? decodeStr(returnData) : null;
    });
    if ((i / B) % 20 === 0) { fs.writeFileSync(OUT, JSON.stringify(out)); console.log(i + chunk.length, '/', jobs.length); }
    await sleep(250);
  }
  fs.writeFileSync(OUT, JSON.stringify(out));
  const c = {}; for (const v of Object.values(out.dec)) c[v] = (c[v] || 0) + 1;
  console.log('decimals histogram', JSON.stringify(c));
})();
