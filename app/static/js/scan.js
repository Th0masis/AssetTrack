/**
 * Inicializuje QR skener.
 * onDecoded: callback(code) NEBO string s '__CODE__' pro redirect.
 * Scanner NEOPOUŠTÍ stránku — volání onDecoded nechá rozhodnutí na volajícím.
 * Cooldown 2,5 s zabrání opakovanému skenování stejného kódu.
 */
function initScanner(onDecoded) {
  var el = document.getElementById('qr-reader');

  if (!window.isSecureContext) {
    if (el) el.innerHTML = '<p class="scan-hint">Kamera vyžaduje HTTPS připojení. Použij ruční zadání níže.</p>';
    return;
  }

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    if (el) el.innerHTML = '<p class="scan-hint">Kamera není v tomto prohlížeči podporována. Použij ruční zadání níže.</p>';
    return;
  }

  var lastCode = '';
  var lastTime = 0;
  var COOLDOWN = 2500;

  var scanner = new Html5Qrcode('qr-reader');
  scanner.start(
    { facingMode: 'environment' },
    { fps: 10, qrbox: { width: 220, height: 220 }, aspectRatio: 1.0 },
    function(decoded) {
      var code = decoded.includes('/scan/')
        ? decoded.split('/scan/').pop()
        : decoded.trim();
      var now = Date.now();
      if (code === lastCode && (now - lastTime) < COOLDOWN) return;
      lastCode = code;
      lastTime = now;
      if (typeof onDecoded === 'function') {
        onDecoded(code);
      } else {
        // Zpětná kompatibilita: string s '__CODE__' jako redirect URL
        scanner.stop().then(function() {
          window.location = onDecoded.replace('__CODE__', encodeURIComponent(code));
        });
      }
    },
    function() {}
  ).catch(function(err) {
    if (el) {
      var msg = 'Kamera není dostupná. Použij ruční zadání níže.';
      if (err && (err.toString().includes('NotAllowed') || err.toString().includes('Permission'))) {
        msg = 'Přístup ke kameře byl zamítnut. Povol přístup v nastavení prohlížeče a obnov stránku.';
      } else if (err && err.toString().includes('NotFound')) {
        msg = 'Kamera nenalezena. Použij ruční zadání níže.';
      }
      el.innerHTML = '<p class="scan-hint">' + msg + '</p>';
    }
  });
}
