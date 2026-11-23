import { CaretLeftIcon, InfoIcon, MagnifyingGlassIcon, PersonIcon } from "@phosphor-icons/react/ssr";
import Link from "next/link";
import type { ReactNode } from "react";

import styles from "./Gnb.module.css";

/** 로고: 사람 미터 심볼 + 워드마크 */
export function Logo() {
  return (
    <Link href="/" className={styles.logo} aria-label="거기붐벼? 홈">
      <span className={styles.logoMeter} aria-hidden="true">
        <PersonIcon size={14} weight="fill" />
        <PersonIcon size={14} weight="fill" />
        <PersonIcon size={14} weight="fill" />
        <PersonIcon size={14} weight="regular" className={styles.logoMeterEmpty} />
      </span>
      거기붐벼?
    </Link>
  );
}

/** 홈 헤더: 로고 · 검색 · 정보 */
export function MainGnb() {
  return (
    <header className={`${styles.gnb} ${styles.main}`}>
      <Logo />
      <span className={styles.spacer} />
      <Link href="/search" className={styles.iconButton} aria-label="장소 검색">
        <MagnifyingGlassIcon size={24} aria-hidden="true" />
      </Link>
      <Link href="/about" className={styles.iconButton} aria-label="서비스 소개와 데이터 출처">
        <InfoIcon size={24} aria-hidden="true" />
      </Link>
    </header>
  );
}

/** 서브 화면 헤더: 뒤로가기 · 제목 · (오른쪽 버튼) */
export function SubGnb({
  title,
  backHref = "/",
  action,
}: {
  title: string;
  backHref?: string;
  action?: ReactNode;
}) {
  return (
    <header className={styles.gnb}>
      <Link href={backHref} className={styles.iconButton} aria-label="뒤로">
        <CaretLeftIcon size={24} aria-hidden="true" />
      </Link>
      <h1 className={styles.title}>{title}</h1>
      {action ?? <span className={styles.iconButton} aria-hidden="true" />}
    </header>
  );
}
