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
    meta: { requiresAuth: true, roles: ["cajero"] },
  },
  {
    path: "/caja",
    name: "Caja",
    component: () => import("./views/CajaView.vue"),
    meta: { requiresAuth: true, roles: ["cajero", "administrador"] },
  },
  {
    path: "/turnos",
    name: "Turnos",
    component: () => import("./views/TurnosView.vue"),
    meta: { requiresAuth: true, roles: ["cajero", "administrador", "empleado"] },
  },
  {
    path: "/pagos",
    name: "Pagos",
    component: () => import("./views/PagosView.vue"),
    meta: { requiresAuth: true, roles: ["cajero", "administrador", "empleado"] },
  },
  {
    path: "/admin",
    name: "Admin",
    component: () => import("./views/AdminView.vue"),
    meta: { requiresAuth: true, roles: ["administrador"] },
  },
  {
    path: "/admin/configuracion",
    name: "Configuracion",
    component: () => import("./views/ConfiguracionView.vue"),
    meta: { requiresAuth: true, roles: ["administrador"] },
  },
  {
    path: "/seguridad",
    name: "Seguridad",
    component: () => import("./views/SeguridadView.vue"),
    meta: { requiresAuth: true },
  },
  { path: "/admin/usuarios", redirect: "/admin", meta: { requiresAuth: true, roles: ["administrador"] } },
  { path: "/admin/productos", redirect: "/admin", meta: { requiresAuth: true, roles: ["administrador"] } },
  { path: "/admin/turnos", redirect: "/turnos", meta: { requiresAuth: true, roles: ["administrador"] } },
  { path: "/admin/reportes", redirect: "/", meta: { requiresAuth: true, roles: ["administrador"] } },
  {
    path: "/clientes",
    name: "Clientes",
    component: () => import("./views/ClientesView.vue"),
    meta: { requiresAuth: true, roles: ["cajero", "administrador"] },
  },
  {
    path: "/compras",
    name: "Compras",
    component: () => import("./views/ComprasView.vue"),
    meta: { requiresAuth: true, roles: ["cajero", "administrador"] },
  },
  {
    path: "/devoluciones",
    name: "Devoluciones",
    component: () => import("./views/DevolucionesView.vue"),
    meta: { requiresAuth: true, roles: ["cajero", "administrador"] },
  },
  {
    path: "/egresos",
    name: "Egresos",
    component: () => import("./views/EgresosView.vue"),
    meta: { requiresAuth: true, roles: ["cajero", "administrador"] },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore();

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: "Login" });
    return;
  }

  if (authStore.isAuthenticated && !authStore.user) {
    await authStore.fetchUser();
  }

  const roles = to.meta.roles as string[] | undefined;
  if (roles && authStore.user && !roles.includes(authStore.user.rol)) {
    next({ name: "Dashboard" });
    return;
  }

  if (to.name === "Login" && authStore.isAuthenticated) {
    next({ name: "Dashboard" });
    return;
  }

  next();
});

export default router;