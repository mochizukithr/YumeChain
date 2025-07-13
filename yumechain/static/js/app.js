document.addEventListener("DOMContentLoaded", function () {
  // スクロール機能の改善版

  // ヘルパー関数: 安全なclassListチェック
  function hasClass(element, className) {
    return (
      element &&
      element.classList &&
      typeof element.classList.contains === "function" &&
      element.classList.contains(className)
    );
  }

  // ヘルパー関数: 安全なclosestチェック
  function findClosest(element, selector) {
    return (
      element &&
      typeof element.closest === "function" &&
      element.closest(selector)
    );
  }

  // デバウンス機能の追加
  function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  // スムーズスクロール関数（改善版）
  function smoothScrollTo(element, offset = 0) {
    if (!element) {
      console.warn("スクロール対象の要素が見つかりません");
      return;
    }

    try {
      const elementPosition =
        element.getBoundingClientRect().top + window.pageYOffset;
      const offsetPosition = Math.max(0, elementPosition - offset);

      window.scrollTo({
        top: offsetPosition,
        behavior: "smooth",
      });
    } catch (error) {
      console.error("スクロール中にエラーが発生しました:", error);
      // フォールバック: 通常のスクロール
      if (element.scrollIntoView) {
        element.scrollIntoView({ behavior: "smooth" });
      }
    }
  }

  // スクロール位置の記憶機能（改善版）
  const saveScrollPosition = debounce(function () {
    try {
      sessionStorage.setItem("scrollPosition", window.pageYOffset.toString());
    } catch (error) {
      console.warn("スクロール位置の保存に失敗しました:", error);
    }
  }, 100);

  function restoreScrollPosition() {
    try {
      const savedPosition = sessionStorage.getItem("scrollPosition");
      if (savedPosition && !isNaN(savedPosition)) {
        window.scrollTo(0, parseInt(savedPosition));
      }
    } catch (error) {
      console.warn("スクロール位置の復元に失敗しました:", error);
    }
  }

  // ページ読み込み時にスクロール位置を復元
  window.addEventListener("load", restoreScrollPosition);

  // ページ離脱時にスクロール位置を保存
  window.addEventListener("beforeunload", saveScrollPosition);

  // モバイルデバイスでのスクロール改善
  function isMobile() {
    return window.innerWidth <= 768;
  }

  // モバイルでのスクロール調整（改善版）
  function mobileScrollTo(element, offset = 0) {
    if (!element) return;

    if (isMobile()) {
      const elementPosition =
        element.getBoundingClientRect().top + window.pageYOffset;
      const offsetPosition = Math.max(0, elementPosition - offset - 10);

      window.scrollTo({
        top: offsetPosition,
        behavior: "smooth",
      });
    } else {
      smoothScrollTo(element, offset);
    }
  }

  // カードクリック時の処理（改善版）
  document.addEventListener("click", function (evt) {
    try {
      const target = evt.target;

      // null チェックを追加
      if (!target) return;

      // 小説カードがクリックされた場合
      if (findClosest(target, ".novel-card")) {
        const mainContent = document.getElementById("main-content");
        const novelsContent = document.getElementById("novels-content");

        if (mainContent && novelsContent) {
          mainContent.style.display = "block";
          novelsContent.style.display = "none";

          // メインコンテンツにスムーズスクロール（改善版）
          setTimeout(() => {
            if (isMobile()) {
              mobileScrollTo(mainContent, 20);
            } else {
              smoothScrollTo(mainContent, 20);
            }
          }, 100);
        }
      }

      // 詳細ボタンがクリックされた場合
      if (
        hasClass(target, "btn") &&
        target.getAttribute &&
        target.getAttribute("hx-target") === "#main-content"
      ) {
        const mainContent = document.getElementById("main-content");
        if (mainContent) {
          mainContent.style.display = "block";

          // 少し遅延してスクロール
          setTimeout(() => {
            if (isMobile()) {
              mobileScrollTo(mainContent, 20);
            } else {
              smoothScrollTo(mainContent, 20);
            }
          }, 150);
        }
      }

      // 戻るボタンがクリックされた場合
      if (hasClass(target, "back-btn") || findClosest(target, ".back-btn")) {
        const novelsContent = document.getElementById("novels-content");
        const mainContent = document.getElementById("main-content");

        if (novelsContent && mainContent) {
          mainContent.style.display = "none";
          novelsContent.style.display = "block";

          setTimeout(() => {
            const novelsSection = document.getElementById("novels-section");
            if (novelsSection) {
              smoothScrollTo(novelsSection, 20);
            }
          }, 100);
        }
      }
    } catch (error) {
      console.error("クリックイベント処理中にエラーが発生しました:", error);
    }
  });

  // HTMXリクエスト完了後の処理（改善版）
  document.body.addEventListener("htmx:afterRequest", function (evt) {
    try {
      if (!evt.detail || !evt.detail.target) return;

      const target = evt.detail.target;

      if (target.id === "novels-content") {
        // 検索結果が表示された場合
        const mainContent = document.getElementById("main-content");
        const novelsContent = document.getElementById("novels-content");

        if (mainContent && novelsContent) {
          mainContent.style.display = "none";
          novelsContent.style.display = "block";

          // 検索結果にスムーズスクロール
          setTimeout(() => {
            if (isMobile()) {
              mobileScrollTo(target, 20);
            } else {
              smoothScrollTo(target, 20);
            }
          }, 100);
        }
      } else if (target.id === "main-content") {
        // 小説詳細やエピソードが読み込まれた場合
        setTimeout(() => {
          if (isMobile()) {
            mobileScrollTo(target, 20);
          } else {
            smoothScrollTo(target, 20);
          }
        }, 100);
      }
    } catch (error) {
      console.error("HTMXリクエスト後の処理中にエラーが発生しました:", error);
    }
  });

  // フォームやボタンのsubmit/click後のスクロール調整
  document.body.addEventListener("htmx:afterSettle", function (evt) {
    try {
      if (!evt.detail || !evt.detail.target) return;

      const target = evt.detail.target;

      // コンテンツが更新された後、適切な位置にスクロール
      if (target.id === "main-content" || target.id === "novels-content") {
        setTimeout(() => {
          if (isMobile()) {
            mobileScrollTo(target, 20);
          } else {
            smoothScrollTo(target, 20);
          }
        }, 50);
      }
    } catch (error) {
      console.error("HTMXセトル後の処理中にエラーが発生しました:", error);
    }
  });

  // キーボードアクセシビリティ: Enterキーでカード選択
  document.addEventListener("keydown", function (evt) {
    try {
      if (!evt.target) return;

      const novelCard = findClosest(evt.target, ".novel-card");
      if (evt.key === "Enter" && novelCard) {
        novelCard.click();
      }
    } catch (error) {
      console.error("キーボードイベント処理中にエラーが発生しました:", error);
    }
  });

  // カードホバーエフェクト
  document.addEventListener(
    "mouseenter",
    function (evt) {
      try {
        if (hasClass(evt.target, "novel-card")) {
          evt.target.style.transform = "translateY(-6px) scale(1.02)";
        }
      } catch (error) {
        console.error(
          "マウスエンターイベント処理中にエラーが発生しました:",
          error
        );
      }
    },
    true
  );

  document.addEventListener(
    "mouseleave",
    function (evt) {
      try {
        if (hasClass(evt.target, "novel-card")) {
          evt.target.style.transform = "";
        }
      } catch (error) {
        console.error(
          "マウスリーブイベント処理中にエラーが発生しました:",
          error
        );
      }
    },
    true
  );
});
