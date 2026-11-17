/* ============================================================
   WebToApp — invisible proof-of-work solver (#244).
   Fetches an adaptive-difficulty challenge from /api/pow/challenge
   and finds a nonce whose sha256(challenge:nonce) has the required
   leading zero bits. Runs in a dedicated Web Worker so the UI never
   janks; falls back to the main thread when Workers are unavailable.
   No captcha, no account, no interaction — at most a brief wait.
   Exposes window.WtaPow.solve() -> {challenge, solution} or null.
   ============================================================ */
(function () {
  'use strict';

  // Worker body: sha256 + leading-zero-bit counter + nonce loop. Kept as a
  // string so it can be loaded from a Blob URL (no extra network request,
  // works under the site CSP).
  var WORKER_SRC = [
    'function lzbits(bytes){var n=0;for(var i=0;i<bytes.length;i++){var b=bytes[i];',
    'if(b===0){n+=8;continue;}for(var s=7;s>=0;s--){if(b&(1<<s))return n;n++;}return n;}return n;}',
    'async function sha256(str){var buf=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(str));return new Uint8Array(buf);}',
    'self.onmessage=async function(e){var challenge=e.data.challenge,bits=e.data.bits;',
    'for(var i=0;i<e.data.maxAttempts;i++){var sol=String(i);',
    'var d=await sha256(challenge+":"+sol);',
    'if(lzbits(d)>=bits){self.postMessage({solution:sol});return;}}',
    'self.postMessage({solution:null});};'
  ].join('\n');

  function leadingZeroBits(bytes) {
    var n = 0;
    for (var i = 0; i < bytes.length; i++) {
      var b = bytes[i];
      if (b === 0) { n += 8; continue; }
      for (var s = 7; s >= 0; s--) {
        if (b & (1 << s)) return n;
        n++;
      }
      return n;
    }
    return n;
  }

  function solveOnMainThread(challenge, bits, maxAttempts) {
    // Fallback for environments without Workers. Yields to the event loop
    // every 256 attempts so the page stays responsive.
    return new Promise(function (resolve) {
      var i = 0;
      function step() {
        var end = Math.min(i + 256, maxAttempts);
        for (; i < end; i++) {
          var sol = String(i);
          var digest = sha256Sync(challenge + ':' + sol);
          if (leadingZeroBits(digest) >= bits) { resolve(sol); return; }
        }
        if (i >= maxAttempts) { resolve(null); return; }
        setTimeout(step, 0);
      }
      step();
    });
  }

  // Minimal synchronous SHA-256 (fallback only; Workers use crypto.subtle).
  function sha256Sync(ascii) {
    function rr(v, n) { return (v >>> n) | (v << (32 - n)); }
    var mathPow = Math.pow, maxWord = mathPow(2, 32);
    var result = '', words = [], asciiBitLength = ascii.length * 8;
    var hash = [], k = [], primeCounter = 0, isComposite = {};
    for (var candidate = 2; primeCounter < 64; candidate++) {
      if (!isComposite[candidate]) {
        for (var i = 0; i < 313; i += candidate) isComposite[i] = candidate;
        hash[primeCounter] = (mathPow(candidate, 0.5) * maxWord) | 0;
        k[primeCounter++] = (mathPow(candidate, 1 / 3) * maxWord) | 0;
      }
    }
    ascii += '\x80';
    while (ascii.length % 64 - 56) ascii += '\x00';
    for (i = 0; i < ascii.length; i++) {
      var j = ascii.charCodeAt(i);
      if (j >> 8) return new Uint8Array(32); // non-ASCII: give up (challenge is ASCII)
      words[i >> 2] |= j << ((3 - i) % 4) * 8;
    }
    words[words.length] = (asciiBitLength / maxWord) | 0;
    words[words.length] = asciiBitLength;
    for (j = 0; j < words.length;) {
      var w = words.slice(j, j += 16), oldHash = hash.slice(0);
      for (i = 0; i < 64; i++) {
        var w15 = w[i - 15], w2 = w[i - 2];
        var a = hash[0], e = hash[4];
        var temp1 = hash[7]
          + (rr(e, 6) ^ rr(e, 11) ^ rr(e, 25))
          + ((e & hash[5]) ^ (~e & hash[6]))
          + k[i]
          + (w[i] = (i < 16) ? w[i] : (
              w[i - 16]
              + (rr(w15, 7) ^ rr(w15, 18) ^ (w15 >>> 3))
              + w[i - 7]
              + (rr(w2, 17) ^ rr(w2, 19) ^ (w2 >>> 10))
            ) | 0);
        var temp2 = (rr(a, 2) ^ rr(a, 13) ^ rr(a, 22))
          + ((a & hash[1]) ^ (a & hash[2]) ^ (hash[1] & hash[2]));
        hash = [(temp1 + temp2) | 0].concat(hash);
        hash[4] = (hash[4] + temp1) | 0;
        hash.length = 8;
      }
      for (i = 0; i < 8; i++) hash[i] = (hash[i] + oldHash[i]) | 0;
    }
    var out = new Uint8Array(32);
    for (i = 0; i < 8; i++) {
      for (var b = 3; b >= 0; b--) {
        out[i * 4 + (3 - b)] = (hash[i] >> (b * 8)) & 255;
      }
    }
    return out;
  }

  function solveInWorker(challenge, bits, maxAttempts) {
    return new Promise(function (resolve) {
      var worker;
      try {
        var blob = new Blob([WORKER_SRC], { type: 'application/javascript' });
        worker = new Worker(URL.createObjectURL(blob));
      } catch (_e) {
        resolve(undefined); // signal: fall back to main thread
        return;
      }
      var timer = setTimeout(function () {
        try { worker.terminate(); } catch (_e) {}
        resolve(null);
      }, 60000);
      worker.onmessage = function (e) {
        clearTimeout(timer);
        try { worker.terminate(); } catch (_e) {}
        resolve(e.data && e.data.solution);
      };
      worker.onerror = function () {
        clearTimeout(timer);
        try { worker.terminate(); } catch (_e) {}
        resolve(undefined);
      };
      worker.postMessage({ challenge: challenge, bits: bits, maxAttempts: maxAttempts });
    });
  }

  async function solve() {
    var res;
    try {
      res = await fetch('/api/pow/challenge');
    } catch (_e) {
      return null;
    }
    if (!res.ok) return null;
    var data = await res.json().catch(function () { return null; });
    if (!data || !data.challenge || !data.bits) return null;
    var maxAttempts = Math.min(1 << Math.min(data.bits + 4, 26), 8000000);
    var solution = await solveInWorker(data.challenge, data.bits, maxAttempts);
    if (solution === undefined) {
      solution = await solveOnMainThread(data.challenge, data.bits, maxAttempts);
    }
    if (solution == null) return null;
    return { challenge: data.challenge, solution: solution };
  }

  window.WtaPow = { solve: solve };
})();