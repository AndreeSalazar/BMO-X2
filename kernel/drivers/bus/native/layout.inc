/* Private mediated USB2 root-device profile, two slots, no user DMA grant. */
#define NATIVE_DMA_PAGES 14
#define NATIVE_CODE_PAGES 2
#define NATIVE_EVENT_BEGIN 0x2000
#define NATIVE_EVENT_END 0x3000
#define NATIVE_SCRATCH_TABLE 0x800
#define NATIVE_SCRATCH_BEGIN 0xa000
#define NATIVE_STATE_BEGIN 0x9800
/* Each 64-byte state: slot,port,speed,kind,config,interface,ep,interval;
 * 8:MPS16 10:report length16 12:DCI 13:cycle 14:configured;
 * 16:control cursor64 24:input ring64 32:pending TRB64;
 * 40:ring index32 44:buffer64 56:report count64. */
#define NS_SLOT 0
#define NS_PORT 1
#define NS_SPEED 2
#define NS_KIND 3
#define NS_CONFIG 4
#define NS_INTERFACE 5
#define NS_ENDPOINT 6
#define NS_INTERVAL 7
#define NS_MPS 8
#define NS_LENGTH 10
#define NS_DCI 12
#define NS_CYCLE 13
#define NS_CONFIGURED 14
#define NS_CONTROL 16
#define NS_RING 24
#define NS_PENDING 32
#define NS_INDEX 40
#define NS_BUFFER 44
#define NS_REPORTS 56
