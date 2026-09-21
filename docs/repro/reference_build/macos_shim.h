// build fix only: glibc's get_current_dir_name() does not exist on macOS
#include <unistd.h>
static inline char* get_current_dir_name() { return getcwd(NULL, 0); }
