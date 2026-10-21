// Fingerprint stabil lintas-periode (FR-22): md5(resto|barang|satuan|kategori).
// SENGAJA TANPA kolom cek/qty — supaya identitas kasus tidak berubah saat ambang ACR
// atau isi baris berubah (menutup gap "fingerprint volatil" Task 31-d).
import { createHash } from "crypto";

export function stableFingerprint(
  restoCode: string,
  itemName: string,
  satuan: string,
  kategori: string,
): string {
  return createHash("md5")
    .update([restoCode, itemName, satuan, kategori].join("|"))
    .digest("hex");
}
