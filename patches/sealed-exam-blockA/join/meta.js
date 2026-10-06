#!/usr/bin/env node
// sealed-exam-blockA exam copy: see join/make_join.py and the .diff beside this file
// meta.js — pool/token metadata for the v4 join. READ-ONLY on the estate; writes only into this folder.
// Sources: noxabot state/v4-poolkeys.json (tok -> the pool key the locked tape follows), wick-engine
// robinhood-v4-births.ndjson (every v4 Initialize since ~2026-08-03: poolId, currencies, venue, hook, birth),
// state/hook-pad-map.json (hook -> padKey where resolved), state/uniswap-launches.json (tok -> launcher `src`).
// Out: meta.json { pools: {poolId: [tok, c0, c1, fee, tickSpacing, hook, venue, birthBlk, birthTs]}, mainPool: {tok: poolId}, launcher: {tok: src}, padKey: {hook: padKey} }
'use strict';
const fs = require('fs'), path = require('path'), readline = require('readline');
const { ethers } = require('/home/green/noxabot/node_modules/ethers');
const HERE = '/home/green/projects/patches/sealed-exam-blockA/work/v4join';
const NOX = '/home/green/projects/patches/sealed-exam-blockA/work/ledgers/state';   // the runner's hashed snapshot
const BIRTHS = '/home/green/projects/patches/sealed-exam-blockA/work/ledgers/robinhood-v4-births.ndjson';   // the runner's hashed snapshot
const abi = ethers.utils.defaultAbiCoder;
const poolIdOf = k => ethers.utils.keccak256(abi.encode(['address', 'address', 'uint24', 'int24', 'address'], [k.currency0, k.currency1, k.fee, k.tickSpacing, k.hooks])).toLowerCase();
const lc = s => (s || '').toLowerCase();

(async () => {
  const pools = {}, mainPool = {}, launcher = {}, padKey = {};
  let nb = 0;
  const rl = readline.createInterface({ input: fs.createReadStream(BIRTHS), crlfDelay: Infinity });
  for await (const ln of rl) {
    if (!ln) continue; let r; try { r = JSON.parse(ln); } catch { continue; }
    nb++;
    const id = lc(r.id); if (pools[id]) continue;
    pools[id] = [lc(r.tok), lc(r.currency0), lc(r.currency1), r.fee, r.tickSpacing, lc(r.hook) || null, r.venue || null, r.birthBlk || null, r.birthTs || null];
  }
  const keys = JSON.parse(fs.readFileSync(path.join(NOX, 'v4-poolkeys.json'), 'utf8'));
  let nk = 0, kNew = 0;
  for (const [tok, v] of Object.entries(keys)) {
    if (!v || !v.key) continue; nk++;
    const k = v.key, id = poolIdOf(k);
    mainPool[lc(tok)] = id;
    if (!pools[id]) { kNew++; pools[id] = [lc(tok), lc(k.currency0), lc(k.currency1), k.fee, k.tickSpacing, lc(k.hooks) === '0x0000000000000000000000000000000000000000' ? null : lc(k.hooks), null, v.block || null, null]; }
  }
  for (const l of JSON.parse(fs.readFileSync(path.join(NOX, 'uniswap-launches.json'), 'utf8')).launches || []) if (l.src) launcher[lc(l.tok)] = lc(l.src);
  const hm = JSON.parse(fs.readFileSync(path.join(NOX, 'hook-pad-map.json'), 'utf8')).hooks || {};
  for (const [h, v] of Object.entries(hm)) if (v && v.padKey) padKey[lc(h)] = v.padKey;
  fs.writeFileSync(path.join(HERE, 'meta.json'), JSON.stringify({ at: new Date().toISOString(), pools, mainPool, launcher, padKey }));
  console.log(`births rows ${nb} · pools ${Object.keys(pools).length} · poolkeys ${nk} (${kNew} not in births) · launcher ${Object.keys(launcher).length} · padKey ${Object.keys(padKey).length}`);
})();
