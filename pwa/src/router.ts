import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";
import { useAuthStore } from "./stores/auth";

const routes: RouteRecordRaw[] = [
  {
    path: "/login",
    name: "Login",
    component: () => import("./views/LoginView.vue"),
    meta: { requiresAuth: false },
  },
  {
    path: "/",
    name: "Dashboard",
    component: () => import("./views/DashboardView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/pos",
    name: "POS",
    component: () => import("./views/POSView.vue"),
    meta: { requiresAuth: true, requiresCaja: true },
  },
  {
    path: "/turnos",
    name: "Turnos",
    component: () => import("./views/TurnosView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/pagos",
    name: "Pagos",
    component: () => import("./views/PagosView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/admin",
    name: "Admin",
    component: () => import("./views/AdminView.vue"),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
  {
    path: "/admin/configuracion",
    name: "Configuracion",
    component: () => import("./views/ConfiguracionView.vue"),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
  {
    path: "/clientes",
    name: "Clientes",
    component: () => import("./views/ClientesView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/compras",
    name: "Compras",
    component: () => import("./views/ComprasView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/devoluciones",
    name: "Devoluciones",
    component: () => import("./views/DevolucionesView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/egresos",
    name: "Egresos",
    component: () => import("./views/EgresosView.vue"),
    meta: { requiresAuth: true },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore();

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: "Login" });
  } else if (to.meta.requiresAdmin && authStore.user?.rol !== "administrador") {
    next({ name: "Dashboard" });
  } else if (to.name === "Login" && authStore.isAuthenticated) {
    next({ name: "Dashboard" });
  } else {
    next();
  }
});

export default router;
