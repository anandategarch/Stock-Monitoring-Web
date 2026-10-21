// Tab ☑ Follow Up 2.0 — kasus lintas-periode (bukan per-snapshot): workflow
// PENDING → DIPROSES → SELESAI/DIBATALKAN + reopen, PIC dropdown/teks bebas (FR-42),
// alasan + kategori tindakan + qty temuan fisik (FR-41), timeline ter-audit (FR-40..44).
"use client";

import { useMemo, useState } from "react";
import {
  CheckCircle2, ChevronRight, ClipboardList, Clock, Fingerprint, History, Loader2,
  Play, RotateCcw, Save, Undo2, UserRound, XCircle,
} from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import {
  useCaseEvent, useFollowupCase, useFollowups, useOverview, usePics, useUpdateCase,
} from "@/hooks/use-sm-api";
import { useDebounced } from "@/hooks/use-debounced";
import { CaseStatusBadge } from "@/components/smweb/badges";
import { EmptyState } from "@/components/smweb/empty-state";
import { StatCard } from "@/components/smweb/stat-card";
import {
  CASE_STATUSES, CASE_STATUS_LABEL, KATEGORI_TINDAKAN,
} from "@/lib/types";
import type { CaseEventRequest, FollowUpCaseDto, FollowUpEventDto } from "@/lib/types";
import {
  fmtDateTime, fmtDateTimeShort, fmtInt, fmtRp, fmtSignedQty, periodLabel,
  signedQtyClass, signedRpClass,
} from "@/lib/format";

type CaseStatus = FollowUpCaseDto["status"];

/** Peta tombol aksi per status saat ini — kunci = status kasus, isi = transisi sah (server memvalidasi ulang). */
const TRANSITIONS: Record<CaseStatus, { to: CaseStatus; label: string; icon: typeof Play; destructive?: boolean }[]> = {
  PENDING: [
    { to: "DIPROSES", label: "Proses", icon: Play },
    { to: "SELESAI", label: "Selesaikan", icon: CheckCircle2 },
    { to: "DIBATALKAN", label: "Batalkan", icon: XCircle, destructive: true },
  ],
  DIPROSES: [
    { to: "SELESAI", label: "Selesaikan", icon: CheckCircle2 },
    { to: "DIBATALKAN", label: "Batalkan", icon: XCircle, destructive: true },
    { to: "PENDING", label: "Kembalikan ke Pending", icon: Undo2 },
  ],
  SELESAI: [{ to: "PENDING", label: "Reopen kasus", icon: RotateCcw }],
  DIBATALKAN: [{ to: "PENDING", label: "Reopen kasus", icon: RotateCcw }],
};

/** Alasan wajib saat menutup (SELESAI/DIBATALKAN) atau membuka kembali (reopen) — server memvalidasi sama (FR-41). */
function isAlasanWajib(from: CaseStatus, to: CaseStatus): boolean {
  const closing = to === "SELESAI" || to === "DIBATALKAN";
  const reopening = (from === "SELESAI" || from === "DIBATALKAN") && to === "PENDING";
  return closing || reopening;
}

const PIC_MANUAL = "__manual__";
const KATEGORI_NONE = "__none__";

export default function FollowUpTab() {
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [q, setQ] = useState("");
  const [restoFilter, setRestoFilter] = useState<string>("ALL");
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);

  const qDebounced = useDebounced(q, 300);

  // qs gabungan status=&resto=&q= (URL-encode via URLSearchParams — server memfilter q).
  const qs = useMemo(() => {
    const params = new URLSearchParams();
    params.set("status", statusFilter === "ALL" ? "" : statusFilter);
    params.set("resto", restoFilter === "ALL" ? "" : restoFilter);
    params.set("q", qDebounced.trim());
    return params.toString();
  }, [statusFilter, restoFilter, qDebounced]);

  const { data: ovs } = useOverview(); // angka ringkas + opsi resto (fallback 0 saat belum termuat)
  const casesCount = ovs?.cases ?? { pending: 0, diproses: 0, selesai: 0, dibatalkan: 0, total: 0 };
  const restoOptions = ovs?.restos ?? [];

  const { data, isPending, error } = useFollowups(qs);
  const cases = data?.cases ?? [];
  const selectedRow = useMemo(
    () => cases.find((c) => c.id === selectedCaseId) ?? null,
    [cases, selectedCaseId],
  );

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <ClipboardList className="h-5 w-5 text-emerald-600" aria-hidden /> ☑ Follow Up 2.0
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          Kasus ber-workflow PENDING → DIPROSES → SELESAI/DIBATALKAN + reopen, dengan PIC, alasan,
          dan timeline ter-audit (FR-40..44).
        </p>
      </div>

      {/* Baris ringkas — angka dari useOverview().cases (fallback 0) */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard title="Pending" value={fmtInt(casesCount.pending)} icon={Clock} tone="amber" sub="menunggu tindakan" />
        <StatCard title="Diproses" value={fmtInt(casesCount.diproses)} icon={Loader2} tone="teal" sub="sedang dikerjakan" />
        <StatCard title="Selesai" value={fmtInt(casesCount.selesai)} icon={CheckCircle2} tone="emerald" sub="kasus tertutup" />
        <StatCard title="Dibatalkan" value={fmtInt(casesCount.dibatalkan)} icon={XCircle} tone="neutral" sub="dibatalkan (bisa reopen)" />
      </div>

      {/* Filter bar */}
      <div className="rounded-xl border bg-card p-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <div className="space-y-1.5">
          <Label htmlFor="fu-status">Status</Label>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger id="fu-status" className="w-full" aria-label="Filter status kasus">
              <SelectValue placeholder="Semua" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">Semua</SelectItem>
              {CASE_STATUSES.map((s) => (
                <SelectItem key={s} value={s}>{CASE_STATUS_LABEL[s]}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="fu-q">Pencarian</Label>
          <Input
            id="fu-q"
            placeholder="Nama barang / resto / PIC…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="fu-resto">Resto</Label>
          <Select value={restoFilter} onValueChange={setRestoFilter}>
            <SelectTrigger id="fu-resto" className="w-full" aria-label="Filter resto">
              <SelectValue placeholder="Semua resto" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">Semua resto</SelectItem>
              {restoOptions.map((r) => (
                <SelectItem key={r.restoCode} value={r.restoCode}>
                  {r.restoCode} — {r.restoName}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Tabel kasus */}
      {isPending ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-12" />
          ))}
        </div>
      ) : error ? (
        <EmptyState
          title="Gagal memuat daftar kasus"
          description={error instanceof Error ? error.message : "Permintaan gagal."}
        />
      ) : cases.length === 0 ? (
        <EmptyState
          icon={ClipboardList}
          title="Belum ada kasus"
          description="Tandai baris anomali di tab Deviasi (tombol +FU) untuk membuat kasus pertama."
        />
      ) : (
        <>
          <div className="rounded-xl border bg-card overflow-hidden">
            <div className="max-h-[70vh] overflow-y-auto nice-scroll">
              <Table>
                <TableHeader className="sticky top-0 z-10 bg-card">
                  <TableRow>
                    <TableHead>Status</TableHead>
                    <TableHead>Resto</TableHead>
                    <TableHead>Barang</TableHead>
                    <TableHead>Kategori</TableHead>
                    <TableHead className="text-right">Deviasi</TableHead>
                    <TableHead className="text-right">Nominal</TableHead>
                    <TableHead>PIC</TableHead>
                    <TableHead>Periode awal</TableHead>
                    <TableHead>Aktivitas terakhir</TableHead>
                    <TableHead className="text-right">Event</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {cases.map((cs) => (
                    <TableRow
                      key={cs.id}
                      tabIndex={0}
                      aria-label={`Buka detail kasus: ${cs.itemName} — ${cs.restoCode}`}
                      className="cursor-pointer hover:bg-muted/50 focus-visible:bg-muted/50 outline-none"
                      onClick={() => setSelectedCaseId(cs.id)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          setSelectedCaseId(cs.id);
                        }
                      }}
                    >
                      <TableCell><CaseStatusBadge status={cs.status} /></TableCell>
                      <TableCell>
                        <span className="font-medium">{cs.restoCode}</span>{" "}
                        <span className="text-xs text-muted-foreground">{cs.restoName}</span>
                      </TableCell>
                      <TableCell>
                        {cs.itemName} <span className="text-xs text-muted-foreground">({cs.satuan})</span>
                      </TableCell>
                      <TableCell className="text-xs">{cs.kategori}</TableCell>
                      <TableCell className={`text-right cell-num ${signedQtyClass(cs.currentQtyDeviasi)}`}>
                        {fmtSignedQty(cs.currentQtyDeviasi)}
                      </TableCell>
                      <TableCell className={`text-right cell-num ${signedRpClass(cs.currentNominal)}`}>
                        {fmtRp(cs.currentNominal)}
                      </TableCell>
                      <TableCell>{cs.pic ?? "—"}</TableCell>
                      <TableCell className="text-xs">{periodLabel(cs.periodFirstSeen)}</TableCell>
                      <TableCell className="text-xs">{fmtDateTimeShort(cs.lastEventAt)}</TableCell>
                      <TableCell className="text-right cell-num">{fmtInt(cs.eventCount)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>

          <p className="text-xs text-muted-foreground flex items-start gap-1.5">
            <Fingerprint className="h-3.5 w-3.5 mt-0.5 shrink-0" aria-hidden />
            Identitas kasus = fingerprint stabil (resto|barang|satuan|kategori — TANPA kolom cek/qty,
            FR-22) sehingga kasus berulang lintas-periode terdeteksi &amp; tidak hilang saat ambang berubah.
          </p>
        </>
      )}

      {/* Dialog detail kasus (lintas-periode — kasus DIBATALKAN/SELESAI tetap bisa dibuka + tombol Reopen) */}
      {selectedCaseId ? (
        <CaseDetailDialog
          caseId={selectedCaseId}
          caseRow={selectedRow}
          onOpenChange={(open) => {
            if (!open) setSelectedCaseId(null);
          }}
        />
      ) : null}
    </div>
  );
}

// ---------- Dialog detail + editor PIC + form transisi + timeline ----------

function CaseDetailDialog({
  caseId,
  caseRow,
  onOpenChange,
}: {
  caseId: string;
  caseRow: FollowUpCaseDto | null;
  onOpenChange: (open: boolean) => void;
}) {
  const { data: detail, isPending: detailPending } = useFollowupCase(caseId);
  const { data: picsData } = usePics();
  const updateCase = useUpdateCase();
  const caseEvent = useCaseEvent();

  // Detail query lebih segar; baris tabel dipakai agar dialog langsung terisi saat detail masih dimuat.
  const c = detail?.case ?? caseRow;
  const events: FollowUpEventDto[] = detail?.events ?? [];

  const [target, setTarget] = useState<CaseStatus | null>(null);
  const [alasan, setAlasan] = useState("");
  const [kategori, setKategori] = useState<string>(KATEGORI_NONE);
  const [qtyTemuanText, setQtyTemuanText] = useState("");

  // Editor PIC (FR-42): dropdown dari OutletPIC outlet ini + opsi tulis manual (teks bebas).
  // Pola "draft": tampilan mengikuti data kasus sampai user mengedit — tanpa sinkronisasi efek.
  const [picDraft, setPicDraft] = useState<{ text: string; mode: "pick" | "manual" } | null>(null);
  const picText = picDraft?.text ?? c?.pic ?? "";
  const picMode: "pick" | "manual" = picDraft?.mode ?? "manual";

  const outletPics = useMemo(
    () => (picsData?.pics ?? []).filter((p) => p.outletCode === c?.restoCode),
    [picsData, c?.restoCode],
  );

  const picUnchanged = picText.trim() === (c?.pic ?? "");
  const picSaveDisabled = picUnchanged || updateCase.isPending || !c;

  const onSavePic = () => {
    if (!c || picSaveDisabled) return;
    updateCase.mutate(
      { id: c.id, body: { pic: picText.trim() } },
      {
        onSuccess: () => setPicDraft(null), // kembali mengikuti nilai tersimpan di server
        onError: (err) => toast.error(err instanceof Error ? err.message : "Gagal menyimpan PIC."),
      },
    );
  };

  const onPickTransition = (to: CaseStatus) => {
    setTarget((cur) => (cur === to ? null : to));
    setAlasan("");
    setKategori(KATEGORI_NONE);
    setQtyTemuanText("");
  };

  const onConfirmTransition = () => {
    if (!c || !target) return;
    const alasanTrim = alasan.trim();
    if (isAlasanWajib(c.status, target) && !alasanTrim) {
      toast.error("Alasan/tindakan wajib diisi untuk menutup atau membuka kembali kasus (FR-41).");
      return;
    }
    let qtyTemuan: number | null = null;
    if (qtyTemuanText.trim() !== "") {
      const n = Number(qtyTemuanText);
      if (!Number.isFinite(n)) {
        toast.error("Qty temuan fisik harus berupa angka.");
        return;
      }
      qtyTemuan = n;
    }
    const body: CaseEventRequest = {
      toStatus: target,
      alasan: alasanTrim || undefined,
      kategoriTindakan: kategori === KATEGORI_NONE ? undefined : kategori,
      qtyTemuan,
    };
    caseEvent.mutate(
      { id: c.id, body },
      {
        onSuccess: () => {
          setTarget(null);
          setAlasan("");
          setKategori(KATEGORI_NONE);
          setQtyTemuanText("");
        },
        onError: (err) => toast.error(err instanceof Error ? err.message : "Gagal mengubah status kasus."),
      },
    );
  };

  const infoItems: { label: string; value: string; numClass?: string; span?: boolean }[] = [
    { label: "Kategori", value: c?.kategori ?? "—" },
    { label: "Satuan", value: c?.satuan ?? "—" },
    { label: "Deviasi qty (kini)", value: fmtSignedQty(c?.currentQtyDeviasi ?? null), numClass: signedQtyClass(c?.currentQtyDeviasi) },
    { label: "Nominal (kini)", value: fmtRp(c?.currentNominal ?? null), numClass: signedRpClass(c?.currentNominal) },
    { label: "Harga", value: fmtRp(c?.currentHarga ?? null) },
    { label: "Periode terpaut", value: c?.currentPeriodKey ? periodLabel(c.currentPeriodKey) : "—" },
    { label: "PIC saat ini", value: c?.pic ?? "—" },
    { label: "Dibuat", value: fmtDateTime(c?.createdAt ?? null) },
    { label: "Ditutup", value: c?.closedAt ? fmtDateTime(c.closedAt) : "—" },
    { label: "Catatan", value: c?.note ?? "—", span: true },
  ];

  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[70vh] overflow-y-auto nice-scroll">
        {!c ? (
          <div className="space-y-3 py-8">
            <Skeleton className="h-6 w-2/3" />
            <Skeleton className="h-24" />
            <p className="text-sm text-muted-foreground text-center">Memuat detail kasus…</p>
          </div>
        ) : (
          <div className="space-y-5">
            <DialogHeader>
              <DialogTitle className="flex flex-wrap items-center gap-2 text-base leading-snug">
                <span className="font-semibold">{c.itemName}</span>
                <span className="text-sm font-normal text-muted-foreground">
                  · {c.restoCode} ({c.restoName})
                </span>
                <CaseStatusBadge status={c.status} />
              </DialogTitle>
              <DialogDescription className="flex items-center gap-1.5">
                <Fingerprint className="h-3.5 w-3.5 shrink-0" aria-hidden />
                <span className="font-mono text-xs">{c.fingerprint}</span>
                <span className="text-xs">· fingerprint stabil (FR-22)</span>
              </DialogDescription>
            </DialogHeader>

            {/* Info grid */}
            <dl className="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-3">
              {infoItems.map((it) => (
                <div key={it.label} className={it.span ? "col-span-2 sm:col-span-3 space-y-0.5" : "space-y-0.5"}>
                  <dt className="text-xs text-muted-foreground">{it.label}</dt>
                  <dd className={`text-sm ${it.numClass ?? ""}`}>{it.value}</dd>
                </div>
              ))}
            </dl>

            <Separator />

            {/* Editor PIC (FR-42: dropdown OutletPIC + teks bebas) */}
            <section className="rounded-lg border bg-muted/30 p-3 space-y-3" aria-label="Editor PIC">
              <div className="flex items-center gap-2">
                <UserRound className="h-4 w-4 text-muted-foreground" aria-hidden />
                <h3 className="text-sm font-medium">PIC</h3>
                <span className="text-xs text-muted-foreground">dropdown outlet + tulis manual (FR-42)</span>
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                <Select
                  value={picMode === "manual" ? PIC_MANUAL : picText}
                  onValueChange={(v) => {
                    if (v === PIC_MANUAL) {
                      setPicDraft({ text: picText, mode: "manual" });
                    } else {
                      setPicDraft({ text: v, mode: "pick" });
                    }
                  }}
                >
                  <SelectTrigger className="w-full" aria-label="Pilih PIC dari daftar outlet atau tulis manual">
                    <SelectValue placeholder="Pilih PIC…" />
                  </SelectTrigger>
                  <SelectContent>
                    {outletPics.map((p) => (
                      <SelectItem key={p.id} value={p.picName}>
                        {p.picName}{p.waNumber ? <span className="text-muted-foreground"> · {p.waNumber}</span> : null}
                      </SelectItem>
                    ))}
                    <SelectItem value={PIC_MANUAL}>✍ Tulis manual…</SelectItem>
                  </SelectContent>
                </Select>
                <Input
                  aria-label="Nama PIC (teks bebas)"
                  placeholder={picMode === "manual" ? "Nama PIC bebas…" : "Terisi dari pilihan dropdown"}
                  value={picText}
                  onChange={(e) => setPicDraft({ text: e.target.value, mode: "manual" })}
                />
              </div>
              <div className="flex items-center gap-2">
                <Button size="sm" onClick={onSavePic} disabled={picSaveDisabled} aria-label="Simpan PIC kasus">
                  <Save className="h-3.5 w-3.5" aria-hidden /> Simpan PIC
                </Button>
                {updateCase.isPending ? (
                  <span className="text-xs text-muted-foreground flex items-center gap-1">
                    <Loader2 className="h-3 w-3 animate-spin" aria-hidden /> menyimpan…
                  </span>
                ) : null}
              </div>
            </section>

            {/* Form transisi status (peta transisi server: FR-40 + reopen) */}
            <section className="rounded-lg border p-3 space-y-3" aria-label="Aksi status kasus">
              <h3 className="text-sm font-medium">Aksi status</h3>
              <div className="flex flex-wrap gap-2">
                {TRANSITIONS[c.status].map((tr) => {
                  const Icon = tr.icon;
                  const active = target === tr.to;
                  return (
                    <Button
                      key={tr.to}
                      size="sm"
                      variant={active ? "default" : tr.destructive ? "destructive" : "outline"}
                      onClick={() => onPickTransition(tr.to)}
                      aria-pressed={active}
                    >
                      <Icon className="h-3.5 w-3.5" aria-hidden /> {tr.label}
                    </Button>
                  );
                })}
              </div>

              {target ? (
                <div className="rounded-md border bg-muted/30 p-3 space-y-3">
                  <p className="text-xs text-muted-foreground">
                    Transisi {c.status} → <strong>{target}</strong>
                    {isAlasanWajib(c.status, target)
                      ? " — alasan/tindakan WAJIB (menutup/reopen kasus)."
                      : " — alasan opsional untuk transisi ini."}
                  </p>
                  <div className="space-y-1.5">
                    <Label htmlFor={`fu-alasan-${caseId}`}>Alasan / tindakan</Label>
                    <Textarea
                      id={`fu-alasan-${caseId}`}
                      placeholder="Contoh: SO ulang 12 Okt — selisih fisik 2 dus disetujui TL…"
                      value={alasan}
                      onChange={(e) => setAlasan(e.target.value)}
                      rows={2}
                    />
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="space-y-1.5">
                      <Label htmlFor={`fu-kategori-${caseId}`}>Kategori tindakan</Label>
                      <Select value={kategori} onValueChange={setKategori}>
                        <SelectTrigger id={`fu-kategori-${caseId}`} className="w-full" aria-label="Kategori tindakan">
                          <SelectValue placeholder="Tanpa kategori" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value={KATEGORI_NONE}>— Tanpa kategori —</SelectItem>
                          {KATEGORI_TINDAKAN.map((k) => (
                            <SelectItem key={k} value={k}>{k}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor={`fu-temuan-${caseId}`}>Qty temuan fisik (opsional)</Label>
                      <Input
                        id={`fu-temuan-${caseId}`}
                        type="number"
                        step="any"
                        placeholder="mis. -2"
                        value={qtyTemuanText}
                        onChange={(e) => setQtyTemuanText(e.target.value)}
                      />
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      onClick={onConfirmTransition}
                      disabled={caseEvent.isPending}
                      aria-label={`Konfirmasi ubah status ke ${target}`}
                    >
                      {caseEvent.isPending ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
                      ) : (
                        <CheckCircle2 className="h-3.5 w-3.5" aria-hidden />
                      )}
                      Konfirmasi
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => setTarget(null)}>Batal</Button>
                  </div>
                </div>
              ) : null}
            </section>

            {/* Timeline (FR-41) */}
            <section className="space-y-3" aria-label="Timeline peristiwa kasus">
              <h3 className="text-sm font-medium flex items-center gap-2">
                <History className="h-4 w-4 text-muted-foreground" aria-hidden /> Timeline ({events.length} event)
              </h3>
              {detailPending ? (
                <div className="space-y-2">
                  <Skeleton className="h-14" />
                  <Skeleton className="h-14" />
                </div>
              ) : events.length === 0 ? (
                <p className="text-sm text-muted-foreground">Belum ada event — riwayat transisi akan tampil di sini.</p>
              ) : (
                <ol>
                  {events.map((ev, idx) => (
                    <li key={ev.id} className="relative pl-6 pb-4 last:pb-0">
                      {idx < events.length - 1 ? (
                        <span className="absolute left-[5px] top-2 bottom-0 w-px bg-border" aria-hidden="true" />
                      ) : null}
                      <span className="absolute left-0 top-1 h-3 w-3 rounded-full bg-emerald-500 border-2 border-card" aria-hidden="true" />
                      <div className="space-y-1">
                        <p className="text-xs text-muted-foreground">
                          {fmtDateTime(ev.createdAt)} · aktor <strong className="font-medium">{ev.actor}</strong>
                        </p>
                        <p className="flex flex-wrap items-center gap-1 text-xs">
                          <CaseStatusBadge status={ev.fromStatus} />
                          <ChevronRight className="h-3 w-3 text-muted-foreground" aria-hidden />
                          <CaseStatusBadge status={ev.toStatus} />
                        </p>
                        {ev.alasan ? <p className="text-sm">{ev.alasan}</p> : null}
                        <p className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                          {ev.kategoriTindakan ? <Badge variant="outline">{ev.kategoriTindakan}</Badge> : null}
                          {ev.qtyTemuan !== null ? (
                            <span className="cell-num">temuan fisik: {fmtSignedQty(ev.qtyTemuan)}</span>
                          ) : null}
                        </p>
                      </div>
                    </li>
                  ))}
                </ol>
              )}
            </section>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
