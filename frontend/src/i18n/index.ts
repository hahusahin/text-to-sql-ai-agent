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
  hideSql: string;
  noRows: string;
  error: string;
  aboutButton: string;
  aboutTitle: string;
  aboutBody: string;
};

export const dictionaries: Record<Language, Dictionary> = {
  en: {
    title: "Manufacturing Text-to-SQL Assistant",
    description:
      "An AI assistant that turns your plain-language questions into SQL and answers them from a real manufacturing factory's database.",
    dataNote:
      "This factory builds switchgear panels, contactors, motors, transformers, and control units. Behind the assistant is a year of data on what each line produced, when machines went down and why, and how quality inspections turned out. Ask about production, scrap, downtime, or defects — or tap an example to start.",
    examplesHeading: "Try one of these:",
    examples: [
      "Which production line has accumulated the most unplanned downtime, and how many minutes in total?",
      "Break down total downtime minutes by reason code, from worst to least.",
      "What is the scrap rate for each product category?",
      "Which production lines have unplanned downtime above the per-line average?",
    ],
    inputPlaceholder: "Ask a question about the factory's data…",
    askButton: "Ask",
    askingButton: "Asking…",
    showSql: "Show SQL",
    hideSql: "Hide SQL",
    noRows: "No rows returned.",
    error: "Something went wrong. Is the AI service running?",
    aboutButton: "About",
    aboutTitle: "About this factory & its data",
    aboutBody: `**What this factory makes**

A discrete-manufacturing plant that builds industrial electrical equipment: switchgear panels, contactors, motors, transformers, and control units.

**The data behind the assistant** (about 12 months)

- **Production lines & machines** — the cells on the shop floor and the machines on each line.
- **Shifts** — Morning, Evening, and Night.
- **Work orders** — a batch of one product scheduled on a line, with a planned quantity and a status.
- **Production output** — what each work order actually produced, including scrap.
- **Downtime events** — every stop on a line or machine: planned or unplanned, a reason (breakdown, setup/changeover, material shortage, planned maintenance), and how many minutes it lasted.
- **Quality inspections & defects** — QC checks tied to production, and the defects they found by type and severity.

**What you can ask**

Production volumes, scrap rates, downtime by line / machine / reason, quality yield, defects by product, and time-based slices like "last month" or "this quarter". Questions that need several of these tables joined together are exactly where it shines.`,
  },
  tr: {
    title: "Üretim Veritabanı Doğal Dil Asistanı",
    description:
      "Sade dildeki sorularınızı SQL'e çevirip gerçek bir üretim fabrikasının veritabanından yanıtlayan bir yapay zekâ asistanı.",
    dataNote:
      "Fabrika; pano, kontaktör, motor, trafo ve kontrol üniteleri üretir. Asistanın arkasında; her hattın ne ürettiği, makinelerin ne zaman ve neden durduğu ve kalite kontrollerinin nasıl sonuçlandığına dair bir yıllık veri var. Üretim, hurda, duruş veya hatalar hakkında sorun — ya da başlamak için bir örneğe dokunun.",
    examplesHeading: "Şunlardan birini deneyin:",
    examples: [
      "Toplamda en çok plansız duruş biriktiren üretim hattı hangisi ve toplam kaç dakika?",
      "Toplam duruş dakikalarını sebep koduna göre en kötüden en aza sırala.",
      "Her ürün kategorisi için hurda oranı nedir?",
      "Hangi üretim hatlarının plansız duruşu, hat başına ortalamanın üzerinde?",
    ],
    inputPlaceholder: "Fabrikanın verisi hakkında bir soru sorun…",
    askButton: "Sor",
    askingButton: "Soruluyor…",
    showSql: "SQL'i göster",
    hideSql: "SQL'i gizle",
    noRows: "Sonuç satırı yok.",
    error: "Bir şeyler ters gitti. AI servisi çalışıyor mu?",
    aboutButton: "Hakkında",
    aboutTitle: "Bu fabrika ve verisi hakkında",
    aboutBody: `**Bu fabrika ne üretir?**

Endüstriyel elektrik ekipmanı üreten bir imalat tesisi: pano (switchgear), kontaktör, motor, trafo ve kontrol üniteleri.

**Asistanın arkasındaki veri** (yaklaşık 12 ay)

- **Üretim hatları ve makineler** — sahadaki hücreler ve her hattaki makineler.
- **Vardiyalar** — Sabah, Akşam ve Gece.
- **İş emirleri** — bir hatta planlanan, tek bir ürünün partisi; planlanan miktar ve durum bilgisiyle.
- **Üretim çıktısı** — her iş emrinin gerçekte ne ürettiği, hurda dahil.
- **Duruş kayıtları** — bir hat ya da makinedeki her durma: planlı veya plansız, bir sebep (arıza, kurulum/geçiş, malzeme eksikliği, planlı bakım) ve kaç dakika sürdüğü.
- **Kalite kontrolleri ve hatalar** — üretime bağlı QC kontrolleri ve buldukları hatalar (tip ve önem derecesiyle).

**Neler sorabilirsiniz?**

Üretim miktarları, hurda oranları, hat / makine / sebebe göre duruş, kalite verimi, ürüne göre hatalar ve "geçen ay" ya da "bu çeyrek" gibi zaman dilimleri. Asıl gücü, bu tabloların birkaçının birlikte birleştirilmesini (JOIN) gerektiren sorularda ortaya çıkar.`,
  },
};
