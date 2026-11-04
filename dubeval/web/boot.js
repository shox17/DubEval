// The boot screen's words and the place of its bar, set before the first paint (a plain script, so the page waits for
// it): the screen takes over from the desktop app's starting page (desktop/status.html, the same words and shape), and
// an empty title would make everything jump.
(() => {
  const TEXT = {
    en: ["Starting DubEval…", "Loading the speech and video tools. The first start can take up to a minute."],
    ko: ["DubEval 시작 중…", "음성·영상 도구를 불러오고 있습니다. 처음 시작할 때는 1분 정도 걸릴 수 있습니다."],
    pt: ["Iniciando o DubEval…", "Carregando as ferramentas de fala e vídeo. A primeira vez pode levar até um minuto."],
    es: ["Iniciando DubEval…", "Cargando las herramientas de habla y video. La primera vez puede tardar hasta un minuto."],
  };
  let saved = null;
  try { saved = localStorage.getItem("dubeval.lang"); } catch { /* storage may be blocked */ }
  const browser = (navigator.language || "en").split("-")[0];
  const lang = [saved, browser].find(l => l && l in TEXT) || "en";
  document.documentElement.lang = lang;
  document.documentElement.style.setProperty("--sweep", `-${Date.now() % 1600}ms`);   // the bar goes on where it was
  document.getElementById("boot-title").textContent = TEXT[lang][0];
  document.getElementById("boot-text").textContent = TEXT[lang][1];
  document.getElementById("boot").classList.add("ready");
})();
