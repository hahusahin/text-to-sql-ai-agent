/**
 * Static UI strings for the TR/EN toggle.
 *
 * This is the *chrome* only — title, description, buttons, example questions.
 * It does NOT translate the model's answer: the agent already replies in
 * whatever language the question was asked. Switching the toggle never changes
 * an answer that has already come back.
 */

export type Language = "en" | "tr";

export type Dictionary = {
  title: string;
  description: string;
  dataNote: string;
  examplesHeading: string;
  examples: string[];
  inputPlaceholder: string;
  askButton: string;
  askingButton: string;
  showSql: string;
  noRows: string;
  error: string;
};

export const dictionaries: Record<Language, Dictionary> = {
  en: {
    title: "Manufacturing Text-to-SQL Assistant",
    description:
      "Ask plain-language questions about a manufacturing factory's database — production, downtime, and quality data.",
    dataNote:
      "Behind it: products, production lines, machines, shifts, work orders, output, downtime events, and quality inspections over the last year.",
    examplesHeading: "Try one of these:",
    examples: [
      "Which production line had the most unplanned downtime last month?",
      "What is the scrap rate by product?",
      "Top 3 defect types this quarter",
      "How many work orders were completed per shift?",
    ],
    inputPlaceholder: "e.g. How many production lines are there?",
    askButton: "Ask",
    askingButton: "Asking…",
    showSql: "Show SQL",
    noRows: "No rows returned.",
    error: "Something went wrong. Is the AI service running?",
  },
  tr: {
    title: "Üretim Veritabanı Doğal Dil Asistanı",
    description:
      "Bir üretim fabrikasının veritabanına sade dille soru sorun — üretim, duruş ve kalite verileri.",
    dataNote:
      "Arkasında: son bir yıla ait ürünler, üretim hatları, makineler, vardiyalar, iş emirleri, üretim çıktısı, duruş kayıtları ve kalite kontrolleri.",
    examplesHeading: "Şunlardan birini deneyin:",
    examples: [
      "Geçen ay hangi üretim hattında en çok plansız duruş oldu?",
      "Ürüne göre hurda oranı nedir?",
      "Bu çeyrekteki en sık 3 hata tipi",
      "Vardiya başına kaç iş emri tamamlandı?",
    ],
    inputPlaceholder: "örn. Kaç üretim hattı var?",
    askButton: "Sor",
    askingButton: "Soruluyor…",
    showSql: "SQL'i göster",
    noRows: "Sonuç satırı yok.",
    error: "Bir şeyler ters gitti. AI servisi çalışıyor mu?",
  },
};
