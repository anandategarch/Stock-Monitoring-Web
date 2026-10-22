// State UI SM-WEB (Zustand + persist per sesi — INV-8: filter & preferensi persist,
// tapi tidak pernah menimpa kerja user; seleksi kosong tetap jujur).
"use client";

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { MetricKey } from "@/lib/types";

export type TabKey =
  | "overview" | "ingest" | "pivot" | "deviasi" | "selisihin" | "nominal"
  | "laporan" | "followup" | "po" | "dq" | "config";

export interface SmState {
  activeTab: TabKey;
  periodKey: string | null; // null = periode terbaru yang aktif
  setActiveTab: (t: TabKey) => void;
  setPeriodKey: (p: string | null) => void;

  // Tampilan Rapat (Task 33 fitur #1): densitas tabel ala Treeview desktop
  // (zoom 80% → font 8pt / rowheight ±24px) — global, memengaruhi semua tabel.
  uiCompact: boolean;
  setUiCompact: (v: boolean) => void;

  // filter Deviasi (FR-30) — H & ambang ACR satu sumber, sinkron GR/PCS
  devGroup: "GR" | "PCS";
  devResto: string; // "" = semua resto
  devH: number;
  devAmbang: number;
  // Warna ala desktop (Task 33 fitur #2): latar amber kolom kunci + warna teks
  // baris per label CEK utama (mirror deviasi_view.py v3.9.71).
  devRowColor: boolean;
  // Susunan baris (Task 33 fitur #3): "flat" = sort bebas (rank per resto dari
  // server); "kelompok" = dikelompokkan per nama barang ala desktop v3.9.65
  // (sort nama asc lalu |dev| desc, rank method=min per kelompok, dev=0 → kosong).
  devLayout: "flat" | "kelompok";
  setDevGroup: (g: "GR" | "PCS") => void;
  setDevResto: (r: string) => void;
  setDevH: (h: number) => void;
  setDevAmbang: (a: number) => void;
  setDevRowColor: (v: boolean) => void;
  setDevLayout: (l: "flat" | "kelompok") => void;

  // filter Pivot (FR-31)
  pivotMode: "resto" | "tanggal";
  pivotMetric: MetricKey;
  pivotResto: string;
  pivotDay: number;
  pivotFrom: number;
  pivotTo: number | null; // null = sampai akhir bulan
  pivotHideEmpty: boolean;
  // Warna ala desktop (Task 33 fitur #2): baris pastel per metrik JENIS
  // (mirror METRIC_BG pivot_view.py) + sel Selisih IN ≠ 0 merah muda #FFC9C9.
  pivotRowColor: boolean;
  setPivotMode: (m: "resto" | "tanggal") => void;
  setPivotMetric: (metric: MetricKey) => void;
  setPivotResto: (r: string) => void;
  setPivotDay: (d: number) => void;
  setPivotFrom: (f: number) => void;
  setPivotTo: (t: number | null) => void;
  setPivotHideEmpty: (v: boolean) => void;
  setPivotRowColor: (v: boolean) => void;
}

export const useSmStore = create<SmState>()(
  persist(
    (set) => ({
      activeTab: "overview",
      periodKey: null,
      setActiveTab: (t) => set({ activeTab: t }),
      setPeriodKey: (p) => set({ periodKey: p }),

      uiCompact: false,
      setUiCompact: (v) => set({ uiCompact: v }),

      devGroup: "GR",
      devResto: "",
      devH: 25,
      devAmbang: 80,
      devRowColor: false,
      devLayout: "flat",
      setDevRowColor: (v) => set({ devRowColor: v }),
      setDevLayout: (l) => set({ devLayout: l }),
      setDevGroup: (g) => set({ devGroup: g }),
      setDevResto: (r) => set({ devResto: r }),
      setDevH: (h) => set({ devH: Math.min(Math.max(Math.round(h), 1), 31) }),
      setDevAmbang: (a) => set({ devAmbang: Math.min(Math.max(Math.round(a), 1), 200) }),

      pivotMode: "resto",
      pivotMetric: "qtyDeviasi",
      pivotResto: "",
      pivotDay: 25,
      pivotFrom: 26,
      pivotTo: null,
      pivotHideEmpty: true,
      pivotRowColor: false,
      setPivotRowColor: (v) => set({ pivotRowColor: v }),
      setPivotMode: (m) => set({ pivotMode: m }),
      setPivotMetric: (metric) => set({ pivotMetric: metric }),
      setPivotResto: (r) => set({ pivotResto: r }),
      setPivotDay: (d) => set({ pivotDay: Math.min(Math.max(Math.round(d), 1), 31) }),
      setPivotFrom: (f) => set({ pivotFrom: Math.min(Math.max(Math.round(f), 1), 31) }),
      setPivotTo: (t) => set({ pivotTo: t === null ? null : Math.min(Math.max(Math.round(t), 1), 31) }),
      setPivotHideEmpty: (v) => set({ pivotHideEmpty: v }),
    }),
    {
      name: "sm-web-ui-v1",
      storage: createJSONStorage(() => sessionStorage),
      partialize: (s) => ({
        activeTab: s.activeTab,
        periodKey: s.periodKey,
        uiCompact: s.uiCompact,
        devRowColor: s.devRowColor,
        devLayout: s.devLayout,
        pivotRowColor: s.pivotRowColor,
        devGroup: s.devGroup,
        devResto: s.devResto,
        devH: s.devH,
        devAmbang: s.devAmbang,
        pivotMode: s.pivotMode,
        pivotMetric: s.pivotMetric,
        pivotResto: s.pivotResto,
        pivotDay: s.pivotDay,
        pivotFrom: s.pivotFrom,
        pivotTo: s.pivotTo,
        pivotHideEmpty: s.pivotHideEmpty,
      }),
    },
  ),
);
