// Replacement intent for the fixture's single OUTPUT.GZ directory entry.
constexpr unsigned long journal_magic = 0x314a4d42;

bool fat_clear_journal(unsigned char* record) {
    memset(record, 0, fat_sector_size);
    return fat_sector(fat_journal_lba, record, true);
}

bool fat_begin(unsigned char* record, unsigned long old_size, const unsigned* old_chain, unsigned old_count,
               unsigned long new_size, const unsigned* new_chain, unsigned new_count) {
    memset(record, 0, fat_sector_size);
    fat_store(record, journal_magic, 4);
    fat_store(record + 4, old_size, 4);
    fat_store(record + 8, new_size, 4);
    for (unsigned index = 0; index < old_count; ++index) record[12 + index] = old_chain[index];
    for (unsigned index = 0; index < new_count; ++index) record[16 + index] = new_chain[index];
    fat_store(record + 20, crc32_gzip({record, 20}), 4);
    return fat_sector(fat_journal_lba, record, true);
}

bool journal_chain(const unsigned char* chain, unsigned count, unsigned& seen) {
    if (!count) return false;
    for (unsigned index = 0; index < fat_max_clusters; ++index) {
        const unsigned cluster = chain[index];
        if (index >= count) {
            if (cluster) return false;
        } else {
            if (!fat_pool_cluster(cluster) || (seen & (1u << cluster))) return false;
            seen |= 1u << cluster;
        }
    }
    return true;
}

struct JournalLink {
    unsigned cluster;
    unsigned next;
    bool keep;
};

bool fat_recover(unsigned char* root, unsigned char* table, unsigned char* mirror) {
    unsigned char record[fat_sector_size];
    if (fat_word(table + 26) != 0xfff7 || fat_word(mirror + 26) != 0xfff7 ||
        !fat_sector(fat_journal_lba, record, false)) return false;
    bool empty = true;
    for (unsigned index = 0; index < fat_sector_size; ++index) empty = empty && !record[index];
    if (empty) {
        for (unsigned index = 0; index < fat_sector_size; ++index) {
            if (table[index] != mirror[index]) return false;
        }
        return true;
    }
    if (word(record) != journal_magic || word(record + 20) != crc32_gzip({record, 20})) return false;
    for (unsigned index = 24; index < fat_sector_size; ++index) {
        if (record[index]) return false;
    }
    const auto* entry = fat_find(root);
    if (!entry || entry[11] != 0x20 || fat_word(entry + 20)) return false;
    const auto old_size = word(record + 4), new_size = word(record + 8);
    const unsigned old_count = fat_cluster_count(old_size), new_count = fat_cluster_count(new_size);
    const auto* old_chain = record + 12;
    const auto* new_chain = record + 16;
    unsigned seen = 0;
    if (!journal_chain(old_chain, old_count, seen) || !journal_chain(new_chain, new_count, seen)) return false;
    const auto current_size = word(entry + 28);
    const unsigned current_first = fat_word(entry + 26);
    const bool committed = current_first == new_chain[0] && current_size == new_size;
    if (!committed && (current_first != old_chain[0] || current_size != old_size)) return false;

    JournalLink links[2 * fat_max_clusters] = {};
    for (unsigned index = 0; index < old_count; ++index) {
        links[index] = {old_chain[index], index + 1 < old_count ? unsigned(old_chain[index + 1]) : 0xffff,
                        !committed};
    }
    for (unsigned index = 0; index < new_count; ++index) {
        links[old_count + index] = {new_chain[index], index + 1 < new_count ? unsigned(new_chain[index + 1]) : 0xffff,
                                    committed};
    }
    for (unsigned cluster = 0; cluster < fat_sector_size / 2; ++cluster) {
        if (fat_pool_cluster(cluster) && (seen & (1u << cluster))) continue;
        if (fat_word(table + 2 * cluster) != fat_word(mirror + 2 * cluster)) return false;
    }
    for (unsigned index = 0; index < old_count + new_count; ++index) {
        const auto link = links[index];
        const unsigned first = fat_word(table + 2 * link.cluster), second = fat_word(mirror + 2 * link.cluster);
        if ((first != link.next && (link.keep || first)) ||
            (second != link.next && (link.keep || second))) return false;
        fat_store(table + 2 * link.cluster, link.keep ? link.next : 0, 2);
    }
    return fat_sector(1, table, true) && fat_sector(33, table, true) && fat_clear_journal(record);
}
