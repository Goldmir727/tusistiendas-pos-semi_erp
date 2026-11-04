/** Almacenamiento local del POS (IndexedDB, sin dependencias externas). */

const DB_NAME = "tusistiendas";
const DB_VERSION = 1;

let dbPromise: Promise<IDBDatabase> | null = null;

function abrir(): Promise<IDBDatabase> {
  if (dbPromise) return dbPromise;
  dbPromise = new Promise((resolve, reject) => {
    const solicitud = indexedDB.open(DB_NAME, DB_VERSION);
    solicitud.onupgradeneeded = () => {
      const db = solicitud.result;
      if (!db.objectStoreNames.contains("estado")) db.createObjectStore("estado");
      if (!db.objectStoreNames.contains("temporales")) db.createObjectStore("temporales", { keyPath: "id" });
      if (!db.objectStoreNames.contains("productos")) db.createObjectStore("productos", { keyPath: "id_producto" });
      if (!db.objectStoreNames.contains("codigos")) db.createObjectStore("codigos");
      if (!db.objectStoreNames.contains("outbox")) db.createObjectStore("outbox", { keyPath: "uuid" });
    };
    solicitud.onsuccess = () => resolve(solicitud.result);
    solicitud.onerror = () => reject(solicitud.error);
  });
  return dbPromise;
}

function operacion<T>(
  store: string,
  modo: IDBTransactionMode,
  accion: (s: IDBObjectStore) => IDBRequest,
): Promise<T> {
  return abrir().then(
    (db) =>
      new Promise<T>((resolve, reject) => {
        const transaccion = db.transaction(store, modo);
        const solicitud = accion(transaccion.objectStore(store));
        solicitud.onsuccess = () => resolve(solicitud.result as T);
        solicitud.onerror = () => reject(solicitud.error);
      }),
  );
}

export const dbLocal = {
  get: <T>(store: string, key: IDBValidKey) => operacion<T | undefined>(store, "readonly", (s) => s.get(key)),
  put: <T>(store: string, value: T, key?: IDBValidKey) =>
    operacion<IDBValidKey>(store, "readwrite", (s) => (key === undefined ? s.put(value) : s.put(value, key))),
  eliminar: (store: string, key: IDBValidKey) => operacion<undefined>(store, "readwrite", (s) => s.delete(key)),
  getAll: <T>(store: string) => operacion<T[]>(store, "readonly", (s) => s.getAll()),
};
