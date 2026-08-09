from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PeriodContract:
    year: int
    bps_year_id: int | None
    month: int
    minimum_observed_provinces: int


@dataclass(frozen=True, slots=True)
class RegionContract:
    code: str
    name: str


@dataclass(frozen=True, slots=True)
class IndicatorContract:
    code: str
    name: str
    unit: str
    favorable_direction: str
    definition: str
    source_url: str
    reference_period_rule: str
    bps_variable_id: int
    bps_derived_variable_id: int
    bps_derived_period_id: int
    periods: tuple[PeriodContract, ...]
    regions: tuple[RegionContract, ...]
    send_derived_variable_parameter: bool = True
    national_code: str = "9999"

    @property
    def safe_parameters(self) -> dict[str, str]:
        parameters = {
            "model": "data",
            "lang": "ind",
            "domain": "0000",
            "var": str(self.bps_variable_id),
            "th": ";".join(
                str(period.bps_year_id) for period in self.periods if period.bps_year_id is not None
            ),
            "turth": str(self.bps_derived_period_id),
        }
        if self.bps_derived_variable_id != 0 and self.send_derived_variable_parameter:
            parameters["turvar"] = str(self.bps_derived_variable_id)
        return parameters


TPT_CONTRACT = IndicatorContract(
    code="tpt",
    name="Tingkat Pengangguran Terbuka Menurut Provinsi",
    unit="Persen",
    favorable_direction="lower",
    definition="Persentase angkatan kerja yang termasuk pengangguran.",
    source_url=(
        "https://www.bps.go.id/id/statistics-table/3/"
        "V2pOVWJWcHJURGg0U2pONFJYaExhVXB0TUhacVFUMDkjMyMwMDAw/"
        "tingkat-pengangguran-terbuka-tpt-dan-tingkat-partisipasi-angkatan-kerja-"
        "tpak-menurut-provinsi.html?year=2023"
    ),
    reference_period_rule="Gunakan observasi Agustus untuk perbandingan tahunan.",
    bps_variable_id=543,
    bps_derived_variable_id=0,
    bps_derived_period_id=190,
    periods=(
        PeriodContract(2023, 123, 8, 34),
        PeriodContract(2024, 124, 8, 38),
        PeriodContract(2025, 125, 8, 38),
    ),
    regions=(
        RegionContract("1100", "ACEH"),
        RegionContract("1200", "SUMATERA UTARA"),
        RegionContract("1300", "SUMATERA BARAT"),
        RegionContract("1400", "RIAU"),
        RegionContract("1500", "JAMBI"),
        RegionContract("1600", "SUMATERA SELATAN"),
        RegionContract("1700", "BENGKULU"),
        RegionContract("1800", "LAMPUNG"),
        RegionContract("1900", "KEP. BANGKA BELITUNG"),
        RegionContract("2100", "KEP. RIAU"),
        RegionContract("3100", "DKI JAKARTA"),
        RegionContract("3200", "JAWA BARAT"),
        RegionContract("3300", "JAWA TENGAH"),
        RegionContract("3400", "DI YOGYAKARTA"),
        RegionContract("3500", "JAWA TIMUR"),
        RegionContract("3600", "BANTEN"),
        RegionContract("5100", "BALI"),
        RegionContract("5200", "NUSA TENGGARA BARAT"),
        RegionContract("5300", "NUSA TENGGARA TIMUR"),
        RegionContract("6100", "KALIMANTAN BARAT"),
        RegionContract("6200", "KALIMANTAN TENGAH"),
        RegionContract("6300", "KALIMANTAN SELATAN"),
        RegionContract("6400", "KALIMANTAN TIMUR"),
        RegionContract("6500", "KALIMANTAN UTARA"),
        RegionContract("7100", "SULAWESI UTARA"),
        RegionContract("7200", "SULAWESI TENGAH"),
        RegionContract("7300", "SULAWESI SELATAN"),
        RegionContract("7400", "SULAWESI TENGGARA"),
        RegionContract("7500", "GORONTALO"),
        RegionContract("7600", "SULAWESI BARAT"),
        RegionContract("8100", "MALUKU"),
        RegionContract("8200", "MALUKU UTARA"),
        RegionContract("9100", "PAPUA BARAT"),
        RegionContract("9200", "PAPUA BARAT DAYA"),
        RegionContract("9400", "PAPUA"),
        RegionContract("9500", "PAPUA SELATAN"),
        RegionContract("9600", "PAPUA TENGAH"),
        RegionContract("9700", "PAPUA PEGUNUNGAN"),
    ),
)

PROVINCE_REGIONS = TPT_CONTRACT.regions

TPAK_CONTRACT = IndicatorContract(
    code="tpak",
    name="Tingkat Partisipasi Angkatan Kerja Menurut Provinsi",
    unit="Persen",
    favorable_direction="higher",
    definition=("Persentase penduduk usia kerja yang termasuk dalam angkatan kerja."),
    source_url=TPT_CONTRACT.source_url,
    reference_period_rule="Gunakan observasi Agustus untuk perbandingan tahunan.",
    bps_variable_id=2396,
    bps_derived_variable_id=0,
    bps_derived_period_id=255,
    periods=(
        PeriodContract(2023, 123, 8, 34),
        PeriodContract(2024, 124, 8, 38),
        PeriodContract(2025, 125, 8, 38),
    ),
    regions=PROVINCE_REGIONS,
)

POVERTY_RATE_CONTRACT = IndicatorContract(
    code="poverty_rate",
    name="Persentase Penduduk Miskin Menurut Provinsi",
    unit="Persen",
    favorable_direction="lower",
    definition=(
        "Persentase penduduk dengan rata-rata pengeluaran per kapita per bulan di bawah "
        "garis kemiskinan."
    ),
    source_url=(
        "https://www.bps.go.id/id/statistics-table/3/"
        "UkVkWGJVZFNWakl6VWxKVFQwWjVWeTlSZDNabVFUMDkjMw%3D%3D/"
        "jumlah-dan-persentase-penduduk-miskin-menurut-provinsi.html"
    ),
    reference_period_rule="Gunakan total perkotaan dan perdesaan kondisi Maret.",
    bps_variable_id=192,
    bps_derived_variable_id=434,
    bps_derived_period_id=61,
    periods=(
        PeriodContract(2023, 123, 3, 34),
        PeriodContract(2024, 124, 3, 38),
        PeriodContract(2025, 125, 3, 38),
    ),
    regions=PROVINCE_REGIONS,
)

GRDP_PER_CAPITA_CONTRACT = IndicatorContract(
    code="grdp_per_capita_current",
    name="PDRB per Kapita Atas Dasar Harga Berlaku Menurut Provinsi",
    unit="Ribu Rupiah",
    favorable_direction="higher",
    definition=("Produk domestik regional bruto atas dasar harga berlaku dibagi jumlah penduduk."),
    source_url=(
        "https://www.bps.go.id/id/statistics-table/3/"
        "YWtoQlRVZzNiMU5qU1VOSlRFeFZiRTR4VDJOTVVUMDkjMw%3D%3D/"
        "produk-domestik-regional-bruto-per-kapita-atas-dasar-harga-berlaku-"
        "menurut-provinsi"
    ),
    reference_period_rule="Gunakan nilai tahunan harga berlaku seri 2010.",
    bps_variable_id=288,
    bps_derived_variable_id=530,
    bps_derived_period_id=0,
    periods=(
        PeriodContract(2023, 123, 12, 38),
        PeriodContract(2024, 124, 12, 38),
        PeriodContract(2025, 125, 12, 38),
    ),
    regions=PROVINCE_REGIONS,
    send_derived_variable_parameter=False,
)

GRDP_GROWTH_CONTRACT = IndicatorContract(
    code="grdp_growth_constant_2010",
    name="Laju Pertumbuhan PDRB ADHK 2010 Menurut Provinsi",
    unit="Persen",
    favorable_direction="higher",
    definition=("Pertumbuhan tahunan PDRB riil atas dasar harga konstan tahun dasar 2010."),
    source_url=(
        "https://www.bps.go.id/id/statistics-table/3/"
        "WnpCcmNtcE1ibkF5VjFSelJHMUVhRE52WjNWSVp6MDkjMyMwMDAw/"
        "laju-pertumbuhan-produk-domestik-regional-bruto-atas-dasar-harga-"
        "konstan-2010--menurut-provinsi--persen-.html?year=2023"
    ),
    reference_period_rule="Gunakan pertumbuhan tahunan ADHK seri 2010.",
    bps_variable_id=291,
    bps_derived_variable_id=0,
    bps_derived_period_id=0,
    periods=(
        PeriodContract(2023, 123, 12, 38),
        PeriodContract(2024, 124, 12, 38),
        PeriodContract(2025, 125, 12, 38),
    ),
    regions=PROVINCE_REGIONS,
)

HDI_CONTRACT = IndicatorContract(
    code="hdi",
    name="Indeks Pembangunan Manusia Metode Baru Menurut Provinsi",
    unit="Poin Indeks",
    favorable_direction="higher",
    definition=(
        "Indeks komposit capaian kesehatan, pendidikan, dan standar hidup layak "
        "menggunakan metode baru BPS."
    ),
    source_url=(
        "https://www.bps.go.id/id/statistics-table/3/"
        "V25GaFNHaExaMnhITm1sWmRrUlJZelJzYUc1SGR6MDkjMw%3D%3D/"
        "indeks-pembangunan-manusia-menurut-provinsi--2023.html?year=2023"
    ),
    reference_period_rule=(
        "Gunakan seri tahunan metode baru; 2025 tetap missing sampai tersedia di WebAPI."
    ),
    bps_variable_id=494,
    bps_derived_variable_id=0,
    bps_derived_period_id=0,
    periods=(
        PeriodContract(2023, 123, 12, 38),
        PeriodContract(2024, 124, 12, 38),
        PeriodContract(2025, None, 12, 0),
    ),
    regions=PROVINCE_REGIONS,
)

CONTRACTS = {
    contract.code: contract
    for contract in (
        TPT_CONTRACT,
        TPAK_CONTRACT,
        POVERTY_RATE_CONTRACT,
        GRDP_PER_CAPITA_CONTRACT,
        GRDP_GROWTH_CONTRACT,
        HDI_CONTRACT,
    )
}
