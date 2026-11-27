// Included by the bounded FAT16 fixture in msvc_gzip.cpp.
constexpr unsigned fat_root_lba = 65;
constexpr unsigned fat_journal_lba = 78;
constexpr unsigned fat_journal_mirror_lba = 79;
constexpr unsigned fat_sector_size = 512;
constexpr unsigned fat_first_cluster = 4, fat_last_cluster = 12, fat_max_clusters = 4;
constexpr char fat_filename[] = "OUTPUT  GZ ";

unsigned fat_word(const unsigned char* bytes) {
    return bytes[0] | (static_cast<unsigned>(bytes[1]) << 8);
}

bool fat_sector(unsigned lba, unsigned char* sector, bool writing) {
    if (!writing && bmo_invoke(4, 4, 0, lba, 0).status) return false;
    for (unsigned offset = 0; offset < fat_sector_size; offset += 8) {
        if (writing) {
            bmo_word value = 0;
            for (unsigned byte = 0; byte < 8; ++byte) {
                value |= static_cast<bmo_word>(sector[offset + byte]) << (8 * byte);
            }
            if (bmo_invoke(4, 3, value, offset / 8, 0).status) return false;
        } else {
            const auto block = bmo_invoke(4, 5, 0, offset / 8, 0);
            if (block.status) return false;
            for (unsigned byte = 0; byte < 8; ++byte) {
                sector[offset + byte] = static_cast<unsigned char>(block.value >> (8 * byte));
            }
        }
    }
    return !writing || bmo_invoke(4, 4, 1, lba, 0).status == BMO_OK;
}

bool fat_load(unsigned char* root, unsigned char* table, unsigned char* mirror) {
    if (!fat_sector(0, mirror, false) || fat_word(mirror + 510) != 0xaa55 ||
        fat_word(mirror + 11) != 512 || mirror[13] != 1 ||
        fat_word(mirror + 14) != 1 || mirror[16] != 2 ||
        fat_word(mirror + 17) != 32 || fat_word(mirror + 19) != 8192 ||
        fat_word(mirror + 22) != 32) return false;
    return fat_sector(1, table, false) && fat_sector(33, mirror, false) &&
           fat_sector(fat_root_lba, root, false);
}

unsigned char* fat_find(unsigned char* root) {
    for (unsigned offset = 0; offset < fat_sector_size; offset += 32) {
        auto* entry = root + offset;
        if (!entry[0]) break;
        unsigned index = 0;
        while (index < 11 && entry[index] == fat_filename[index]) ++index;
        if (index == 11) return entry;
    }
    return nullptr;
}

void fat_store(unsigned char* bytes, unsigned long value, unsigned count) {
    for (unsigned index = 0; index < count; ++index) {
        bytes[index] = static_cast<unsigned char>(value >> (8 * index));
    }
}

unsigned fat_lba(unsigned cluster) {
    return 67 + cluster - 2;
}

bool fat_pool_cluster(unsigned cluster) {
    return cluster >= fat_first_cluster && cluster <= fat_last_cluster && cluster != 5;
}

unsigned fat_cluster_count(unsigned long size) {
    return size && size <= fat_max_clusters * fat_sector_size
        ? (size + fat_sector_size - 1) / fat_sector_size : 0;
}

#include "msvc_gzip_fat_journal.h"

unsigned fat_chain(const unsigned char* entry, const unsigned char* table, unsigned* clusters) {
    if (!entry || entry[11] != 0x20 || fat_word(entry + 20)) return 0;
    const auto size = word(entry + 28);
    const unsigned count = fat_cluster_count(size);
    if (!count) return 0;
    unsigned visited = 0, cluster = fat_word(entry + 26);
    for (unsigned index = 0; index < count; ++index) {
        if (!fat_pool_cluster(cluster) || (visited & (1u << cluster))) {
            return 0;
        }
        visited |= 1u << cluster;
        clusters[index] = cluster;
        cluster = fat_word(table + 2 * cluster);
    }
    return cluster >= 0xfff8 ? count : 0;
}

bool write_disk(const Output& output, bool replace, unsigned cut) {
    if (!output.size || output.size > fat_max_clusters * fat_sector_size) return false;
    unsigned char root[fat_sector_size], table[fat_sector_size], sector[fat_sector_size];
    if (!fat_load(root, table, sector) || !fat_recover(root, table, sector)) return false;
    auto* entry = fat_find(root);
    unsigned previous[fat_max_clusters], previous_count = 0;
    if (replace) {
        previous_count = fat_chain(entry, table, previous);
        if (!previous_count) return false;
    } else {
        if (entry) return false;
        for (unsigned offset = 0; offset < fat_sector_size; offset += 32) {
            if (!root[offset] || root[offset] == 0xe5) {
                entry = root + offset;
                break;
            }
        }
        if (!entry) return false;
    }
    if (!entry) return false;

    const unsigned count = (output.size + fat_sector_size - 1) / fat_sector_size;
    unsigned clusters[fat_max_clusters], free_count = 0;
    for (unsigned cluster = fat_first_cluster; cluster <= fat_last_cluster && free_count < count; ++cluster) {
        if (cluster != 5 && !fat_word(table + 2 * cluster)) clusters[free_count++] = cluster;
    }
    if (free_count != count) return false;
    if (replace) {
        const auto old_size = word(entry + 28);
        unsigned long old_crc = 0;
        if (!fat_payload_crc(previous, previous_count, old_size, sector, old_crc) ||
            !fat_begin(sector, old_size, previous, previous_count, old_crc, output, clusters, count)) return false;
    }

    // Flush the data first, then both FAT copies, then publish the name.
    for (unsigned index = 0; index < count; ++index) {
        const unsigned base = index * fat_sector_size;
        for (unsigned byte = 0; byte < fat_sector_size; ++byte) {
            sector[byte] = base + byte < output.size ? output.bytes[base + byte] : 0;
        }
        if (!fat_sector(fat_lba(clusters[index]), sector, true)) return false;
        fat_store(table + 2 * clusters[index], index + 1 < count ? clusters[index + 1] : 0xffff, 2);
    }
    if (replace) {
        unsigned long written_crc = 0;
        if (!fat_payload_crc(clusters, count, output.size, sector, written_crc) ||
            written_crc != crc32_gzip(output)) return false;
    }
    if (!fat_sector(1, table, true)) return false;
    if (cut == 1) return true;
    if (!fat_sector(33, table, true)) return false;
    if (!replace) {
        for (unsigned index = 0; index < 32; ++index) {
            entry[index] = index < 11 ? fat_filename[index] : 0;
        }
        entry[11] = 0x20;
        fat_store(entry + 24, 0x5d7b, 2);
    }
    fat_store(entry + 26, clusters[0], 2);
    fat_store(entry + 28, output.size, 4);
    if (!fat_sector(fat_root_lba, root, true)) return false;
    if (!replace || cut == 2) return true;
    // The new directory entry already points to the flushed replacement.
    for (unsigned index = 0; index < previous_count; ++index) {
        fat_store(table + 2 * previous[index], 0, 2);
    }
    return fat_sector(1, table, true) && fat_sector(33, table, true) && fat_clear_journal(sector);
}

bool read_disk(Output& input) {
    unsigned char root[fat_sector_size], table[fat_sector_size];
    if (!fat_load(root, table, input.bytes) || !fat_recover(root, table, input.bytes)) return false;
    const auto* entry = fat_find(root);
    unsigned clusters[fat_max_clusters];
    const unsigned count = fat_chain(entry, table, clusters);
    if (!count) return false;
    input.size = word(entry + 28);
    for (unsigned index = 0; index < count; ++index) {
        if (!fat_sector(fat_lba(clusters[index]), input.bytes + index * fat_sector_size, false)) return false;
    }
    return true;
}
