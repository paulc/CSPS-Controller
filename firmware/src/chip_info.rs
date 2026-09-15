pub fn clear_reset() {
    ch32_hal::pac::RCC.rstsckr().modify(|w| w.set_rmvf(true));
}
