/* Live NOVA MARKAT storefront bridge. Product/order data must come from Django, never demo arrays. */
(() => {
  const $ = (id) => document.getElementById(id);
  let liveProducts = [];
  let liveCompanies = [];
  let csrf = "";
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[ch]);
  const moneyLive = (value) => new Intl.NumberFormat("ar-DZ", {
    maximumFractionDigits: 2
  }).format(Number(value) || 0) + " دج";
  async function getCsrf() {
    const response = await fetch("/api/csrf/", { credentials: "same-origin" });
    if (!response.ok) throw new Error("تعذر تهيئة جلسة آمنة.");
    const data = await response.json();
    csrf = data.csrfToken || "";
    return csrf;
  }
  async function apiPost(url, body) {
    if (!csrf) await getCsrf();
    const response = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
      body: JSON.stringify(body)
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || "تعذر تنفيذ الطلب.");
    return data;
  }
  async function syncServerCart() {
    await apiPost("/api/cart/", { items: cart });
  }
  function liveRenderProducts() {
    const target = $("products");
    if (!target) return;
    const q = ($("search")?.value || "").trim().toLocaleLowerCase();
    const list = liveProducts.filter((p) =>
      [p.name, p.category, p.description, p.seller].join(" ").toLocaleLowerCase().includes(q)
    );
    target.innerHTML = list.map((p) => `
      <article class="card">
        <div class="pic">${p.image ? `<img src="${escapeHtml(p.image)}" alt="${escapeHtml(p.name)}" loading="lazy">` : '<span>NOVA</span>'}</div>
        <div class="body">
          <small>${escapeHtml(p.category)}</small>
          <h3>${escapeHtml(p.name)}</h3>
          <p class="muted">${escapeHtml(p.description)}</p>
          <p class="muted">البائع: ${escapeHtml(p.seller)}</p>
          <div class="price">${moneyLive(p.price)}</div>
          <div class="actions">
            <button class="gold" onclick="addLiveProduct(${Number(p.id)})">أضف للسلة</button>
            <button onclick="openLiveProduct(${Number(p.id)})">التفاصيل</button>
          </div>
        </div>
      </article>`).join("") || '<div class="empty">لا توجد منتجات منشورة ومتاحة حاليًا في قاعدة البيانات.</div>';
  }
  window.renderProducts = liveRenderProducts;
  window.addLiveProduct = async (id) => {
    const p = liveProducts.find((x) => Number(x.id) === Number(id));
    if (!p) return;
    try {
      const result = await apiPost(`/api/cart/add/${Number(id)}/`, { quantity: 1 });
      cart[id] = result.quantity;
      try { localStorage.setItem("novaCart", JSON.stringify(cart)); } catch (_) {}
      if ($("cartCount")) $("cartCount").textContent = result.cartCount;
      toast("أُضيف المنتج الحقيقي إلى سلة جلسة المتجر.");
    } catch (error) {
      toast(error.message || "تعذر إضافة المنتج.");
    }
  };
  window.add = window.addLiveProduct;
  window.openLiveProduct = (id) => {
    const p = liveProducts.find((x) => Number(x.id) === Number(id));
    if (!p) return;
    modal(`<h2>${escapeHtml(p.name)}</h2>
      <p class="muted">${escapeHtml(p.description)}</p>
      <p class="price">${moneyLive(p.price)}</p>
      <p>المخزون المتاح: ${Number(p.stock)}</p>
      <p class="muted">البائع: ${escapeHtml(p.seller)}</p>
      <button class="gold" onclick="addLiveProduct(${Number(p.id)});closeModal()">أضف للسلة</button>
      <button onclick="closeModal()">إغلاق</button>`);
  };
  window.details = window.openLiveProduct;
  window.renderCart = () => {
    const box = $("cartBox");
    if (!box) return;
    const entries = Object.entries(cart).filter(([id, qty]) =>
      liveProducts.some((p) => Number(p.id) === Number(id)) && Number(qty) > 0
    );
    if (!entries.length) {
      box.innerHTML = '<div class="empty">السلة فارغة. أضف منتجًا متاحًا من قاعدة البيانات.</div>';
      return;
    }
    let total = 0;
    const rows = entries.map(([id, rawQty]) => {
      const p = liveProducts.find((x) => Number(x.id) === Number(id));
      const qty = Number(rawQty) || 0;
      const subtotal = Number(p.price) * qty;
      total += subtotal;
      return `<div class="panel">
        <div class="head"><div><h3>${escapeHtml(p.name)}</h3><span class="muted">${moneyLive(p.price)} × ${qty}</span></div><strong class="price">${moneyLive(subtotal)}</strong></div>
        <div class="toolbar">
          <button onclick="changeLiveQty(${Number(id)},-1)">−</button>
          <button onclick="changeLiveQty(${Number(id)},1)">+</button>
          <button onclick="removeLiveItem(${Number(id)})">حذف</button>
        </div>
      </div>`;
    }).join("");
    box.innerHTML = rows + `<div class="panel"><h2>الإجمالي: <span class="price">${moneyLive(total)}</span></h2>
      <p class="muted">الدفع عند الاستلام، ويُنشأ الطلب في Django بعد تسجيل الدخول وإكمال بيانات التوصيل.</p>
      <button class="gold" onclick="continueToRealCheckout()">المتابعة إلى السلة الآمنة</button>
    </div>`;
  };
  window.changeLiveQty = async (id, delta) => {
    const p = liveProducts.find((x) => Number(x.id) === Number(id));
    if (!p) return;
    const next = (Number(cart[id]) || 0) + delta;
    if (next <= 0) delete cart[id];
    else if (next > Number(p.stock)) return toast("الكمية تتجاوز المخزون المتاح.");
    else cart[id] = next;
    try {
      await syncServerCart();
      try { localStorage.setItem("novaCart", JSON.stringify(cart)); } catch (_) {}
      if ($("cartCount")) $("cartCount").textContent = Object.values(cart).reduce((n, q) => n + Number(q || 0), 0);
      window.renderCart();
    } catch (error) { toast(error.message || "تعذر تحديث السلة."); }
  };
  window.removeLiveItem = async (id) => {
    delete cart[id];
    try {
      await syncServerCart();
      try { localStorage.setItem("novaCart", JSON.stringify(cart)); } catch (_) {}
      if ($("cartCount")) $("cartCount").textContent = Object.values(cart).reduce((n, q) => n + Number(q || 0), 0);
      window.renderCart();
    } catch (error) { toast(error.message || "تعذر حذف المنتج."); }
  };
  window.saveCart = () => {
    try { localStorage.setItem("novaCart", JSON.stringify(cart)); } catch (_) {}
    syncServerCart().catch((error) => toast(error.message || "تعذر مزامنة السلة."));
  };
  window.checkout = () => window.continueToRealCheckout();
  window.continueToRealCheckout = async () => {
    try {
      await syncServerCart();
      if (!Object.keys(cart).length) return toast("السلة فارغة.");
      window.location.href = "/cart/";
    } catch (error) {
      toast(error.message || "تعذر مزامنة السلة مع الخادم.");
    }
  };
  window.renderDelivery = () => {
    const target = $("companies");
    if (!target) return;
    const q = ($("deliverySearch")?.value || "").trim().toLocaleLowerCase();
    const list = liveCompanies.filter((c) =>
      [c.name, c.description, ...(Array.isArray(c.wilayas) ? c.wilayas : [])].join(" ").toLocaleLowerCase().includes(q)
    );
    target.innerHTML = list.map((c) => `<article class="card"><div class="pic">🚚</div><div class="body">
      <small>شركة توصيل موثّقة على المنصة</small><h3>${escapeHtml(c.name)}</h3>
      <p class="muted">${escapeHtml(c.description || (Array.isArray(c.wilayas) ? c.wilayas.join("، ") : ""))}</p>
      <p>⭐ ${escapeHtml(c.rating)} · ${c.cash_on_delivery ? "الدفع عند الاستلام متاح" : "الدفع عند الاستلام غير مؤكد"}</p>
      <button class="gold" onclick="window.location.href='/delivery/${Number(c.id)}/contact/'">طلب تواصل</button>
      </div></article>`).join("") || '<div class="empty">لا توجد شركات توصيل موثّقة في قاعدة البيانات حاليًا.</div>';
  };
  window.contact = () => toast("اختر شركة موثقة من القائمة للانتقال إلى نموذج التواصل الحقيقي.");
  window.setRole = () => { window.location.href = "/dashboard/"; };
  window.renderDash = () => { window.location.href = "/dashboard/"; };
  window.show = (id) => {
    if (id === "dashboard") return window.location.href = "/dashboard/";
    document.querySelectorAll(".view").forEach((el) => el.classList.add("hidden"));
    const section = $(id);
    if (section) section.classList.remove("hidden");
    if (id === "cart") window.renderCart();
    if (id === "delivery") window.renderDelivery();
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  async function initLiveStore() {
    // The old cart referenced hard-coded demo product IDs; discard those entries once.
    try {
      if (localStorage.getItem("novaLiveCatalogV1") !== "1") {
        localStorage.removeItem("novaCart");
        localStorage.setItem("novaLiveCatalogV1", "1");
      }
      // Demo-only order/contact keys are intentionally cleared; no server orders are deleted.
      localStorage.removeItem("novaOrders");
      localStorage.removeItem("novaLastOrder");
      localStorage.removeItem("novaContactRequests");
    } catch (_) {}
    try {
      await getCsrf();
      const [productsResponse, companiesResponse, cartResponse] = await Promise.all([
        fetch("/api/products/", { credentials: "same-origin" }),
        fetch("/api/delivery-companies/", { credentials: "same-origin" }),
        fetch("/api/cart/", { credentials: "same-origin" })
      ]);
      if (!productsResponse.ok || !companiesResponse.ok || !cartResponse.ok) throw new Error("تعذر تحميل بيانات المتجر.");
      const productData = await productsResponse.json();
      const companyData = await companiesResponse.json();
      const cartData = await cartResponse.json();
      liveProducts = Array.isArray(productData.products) ? productData.products : [];
      liveCompanies = Array.isArray(companyData.companies) ? companyData.companies : [];
      cart = cartData.items && typeof cartData.items === "object" ? cartData.items : {};
      try { localStorage.setItem("novaCart", JSON.stringify(cart)); } catch (_) {}
      window.renderProducts();
      window.renderDelivery();
      if ($("cartCount")) $("cartCount").textContent = String(cartData.cartCount || 0);
    } catch (error) {
      liveProducts = [];
      liveCompanies = [];
      window.renderProducts();
      window.renderDelivery();
      toast("تعذر الاتصال بخادم المتجر. لم نعرض منتجات أو شركات وهمية.");
      console.error("NOVA live connection:", error);
    }
  }
  initLiveStore();
})();
