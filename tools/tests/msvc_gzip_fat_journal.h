// Replacement intent for the fixture's single OUTPUT.GZ directory entry.
constexpr unsigned long journal_magic = 0x324a4d42;
constexpr unsigned journal_record_size = 32;

bool fat_write_journal(unsigned char* record) {
    return fat_sector(fat_journal_lba, record, true) && fat_sector(fat_journal_mirror_lba, record, true);
}

bool fat_clear_journal(unsigned char* record) {
    memset(record, 0, fat_sector_size);
    return fat_write_journal(record);
}

bool fat_payload_crc(const unsigned* chain, unsigned count, unsigned long size,
                     unsigned char* scratch, unsigned long& result) {
    unsigned long crc = 0xffffffff;
    for (unsigned index = 0; index < count; ++index) {
        if (!fat_sector(fat_lba(chain[index]), scratch, false)) return false;
        const unsigned long bytes = size < fat_sector_size ? size : fat_sector_size;
        crc = crc32_update(crc, scratch, bytes);
        size -= bytes;
    }
    result = crc ^ 0xffffffff;
    return true;
}

bool fat_begin(unsigned char* record, unsigned long old_size, const unsigned* old_chain, unsigned old_count,
               unsigned long old_crc, const Output& output, const unsigned* new_chain, unsigned new_count) {
    memset(record, 0, fat_sector_size);
    fat_store(record, journal_magic, 4);
    fat_store(record + 4, old_size, 4);
    fat_store(record + 8, output.size, 4);
    for (unsigned index = 0; index < old_count; ++index) record[12 + index] = old_chain[index];
    for (unsigned index = 0; index < new_count; ++index) record[16 + index] = new_chain[index];
    fat_store(record + 20, old_crc, 4);
    fat_store(record + 24, crc32_gzip(output), 4);
    fat_store(record + 28, crc32_gzip({record, 28}), 4);
    return fat_write_journal(record);
}

bool journal_chain(const unsigned char* bytes, unsigned count, unsigned& seen, unsigned* chain) {
    if (!count) return false;
    for (unsigned index = 0; index < fat_max_clusters; ++index) {
        const unsigned cluster = bytes[index];
        if (index >= count) {
            if (cluster) return false;
        } else {
            if (!fat_pool_cluster(cluster) || (seen & (1u << cluster))) return false;
            seen |= 1u << cluster;
            chain[index] = cluster;
        }
    }
    return true;
}

struct JournalLink {
    unsigned cluster;
    unsigned next;
    bool keep;
};

enum class JournalState { empty, valid, torn };

JournalState journal_state(unsigned char* record) {
    bool empty = true;
    for (unsigned index = 0; index < fat_sector_size; ++index) empty = empty && !record[index];
    if (empty) return JournalState::empty;
    if (word(record) != journal_magic || word(record + 28) != crc32_gzip({record, 28})) {
        return JournalState::torn;
    }
    for (unsigned index = journal_record_size; index < fat_sector_size; ++index) {
        if (record[index]) return JournalState::torn;
    }
    return JournalState::valid;
}

bool journal_link_matches(unsigned value, const JournalLink& link) {
    if (value == link.next) return true;
    const unsigned low = value & 0xff, high = value >> 8;
    return (!low || low == (link.next & 0xff)) && (!high || high == (link.next >> 8));
}

bool journal_directory_matches(const unsigned char* entry, unsigned old_first, unsigned long old_size,
                               unsigned new_first, unsigned long new_size) {
    unsigned char old_fields[6], new_fields[6];
    fat_store(old_fields, old_first, 2);
    fat_store(old_fields + 2, old_size, 4);
    fat_store(new_fields, new_first, 2);
    fat_store(new_fields + 2, new_size, 4);
    for (unsigned index = 0; index < 6; ++index) {
        const unsigned byte = entry[26 + index];
        if (byte != old_fields[index] && byte != new_fields[index]) return false;
    }
    return true;
}

bool fat_recover(unsigned char* root, unsigned char* table, unsigned char* mirror) {
    unsigned char record[fat_sector_size];
    if (fat_word(table + 26) != 0xfff7 || fat_word(mirror + 26) != 0xfff7 ||
        fat_word(table + 28) != 0xfff7 || fat_word(mirror + 28) != 0xfff7 ||
        !fat_sector(fat_journal_lba, record, false)) return false;
    const auto primary = journal_state(record);
    unsigned char first_record[journal_record_size];
    for (unsigned index = 0; index < journal_record_size; ++index) first_record[index] = record[index];
    if (!fat_sector(fat_journal_mirror_lba, record, false)) return false;
    const auto secondary = journal_state(record);
    if (primary == JournalState::empty && secondary == JournalState::empty) {
        for (unsigned index = 0; index < fat_sector_size; ++index) {
            if (table[index] != mirror[index]) return false;
        }
        return true;
    }
    if (primary != JournalState::valid && secondary != JournalState::valid) return false;
    if (primary == JournalState::valid) {
        for (unsigned index = 0; index < journal_record_size; ++index) {
            if (secondary == JournalState::valid && record[index] != first_record[index]) return false;
            record[index] = first_record[index];
        }
    }
    auto* entry = fat_find(root);
    if (!entry || entry[11] != 0x20 || fat_word(entry + 20)) return false;
    const auto old_size = word(record + 4), new_size = word(record + 8);
    const unsigned old_count = fat_cluster_count(old_size), new_count = fat_cluster_count(new_size);
    const auto old_crc = word(record + 20), new_crc = word(record + 24);
    unsigned old_chain[fat_max_clusters], new_chain[fat_max_clusters];
    unsigned seen = 0;
    if (!journal_chain(record + 12, old_count, seen, old_chain) ||
        !journal_chain(record + 16, new_count, seen, new_chain)) return false;
    if (!journal_directory_matches(entry, old_chain[0], old_size, new_chain[0], new_size)) return false;
    const auto current_size = word(entry + 28);
    const unsigned current_first = fat_word(entry + 26);
    unsigned long payload_crc = 0;
    bool committed = current_first == new_chain[0] && current_size == new_size;
    if (committed) {
        if (!fat_payload_crc(new_chain, new_count, new_size, record, payload_crc)) return false;
        committed = payload_crc == new_crc;
    }
    if (!committed && (!fat_payload_crc(old_chain, old_count, old_size, record, payload_crc) ||
                       payload_crc != old_crc)) return false;

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
        if (!journal_link_matches(first, link) || !journal_link_matches(second, link)) return false;
        fat_store(table + 2 * link.cluster, link.keep ? link.next : 0, 2);
    }
    if (!fat_sector(1, table, true) || !fat_sector(33, table, true)) return false;
    if (!committed && (current_first != old_chain[0] || current_size != old_size)) {
        fat_store(entry + 26, old_chain[0], 2);
        fat_store(entry + 28, old_size, 4);
        if (!fat_sector(fat_root_lba, root, true)) return false;
    }
    return fat_clear_journal(record);
}
