/*
  launch-assist-sim site behaviour: theme switch (shared with the examples gallery through the
  "las-theme" storage key), copy buttons on manual code blocks, and the manual chapter list
  that is open on wide screens and folded on phones.
  Copyright (c) 2026 Rahul Singh Khokhar. All rights reserved (see LICENSE).
*/
(function () {
  "use strict";

  // Theme: auto -> light -> dark. The choice is a per-viewer convenience; the page renders
  // correctly without storage.
  var btn = document.getElementById("theme-btn");
  if (btn) {
    var order = ["auto", "light", "dark"];
    var current = function () {
      var t = document.documentElement.getAttribute("data-theme");
      return t === "light" || t === "dark" ? t : "auto";
    };
    var show = function () { btn.textContent = "theme: " + current(); };
    btn.addEventListener("click", function () {
      var next = order[(order.indexOf(current()) + 1) % order.length];
      if (next === "auto") document.documentElement.removeAttribute("data-theme");
      else document.documentElement.setAttribute("data-theme", next);
      try {
        if (next === "auto") localStorage.removeItem("las-theme");
        else localStorage.setItem("las-theme", next);
      } catch (e) { /* storage unavailable: the choice lasts for this page view */ }
      show();
    });
    show();
  }

  // Copy buttons on code blocks in the manual.
  if (navigator.clipboard) {
    document.querySelectorAll(".prose pre").forEach(function (pre) {
      var code = pre.querySelector("code") || pre;
      var holder = document.createElement("div");
      holder.className = "codewrap";
      pre.parentNode.insertBefore(holder, pre);
      var b = document.createElement("button");
      b.type = "button";
      b.className = "copy";
      b.textContent = "copy";
      b.addEventListener("click", function () {
        navigator.clipboard.writeText(code.textContent.replace(/\n$/, "")).then(function () {
          b.textContent = "copied";
          setTimeout(function () { b.textContent = "copy"; }, 1500);
        }, function () { b.textContent = "select and copy"; });
      });
      holder.appendChild(b);
      holder.appendChild(pre);
    });
  }

  // Manual chapter list: open beside the text on wide screens, folded above it on phones.
  var nav = document.querySelector("details.manual-nav");
  if (nav && window.matchMedia) {
    var wide = window.matchMedia("(min-width: 961px)");
    var sync = function () { nav.open = wide.matches; };
    sync();
    if (wide.addEventListener) wide.addEventListener("change", sync);
  }
})();
