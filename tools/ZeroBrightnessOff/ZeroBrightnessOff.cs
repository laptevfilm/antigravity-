using System;
using System.Management;
using System.Runtime.InteropServices;
using System.Threading;
using System.Windows.Forms;

namespace ZeroBrightnessOff
{
    static class Program
    {
        [DllImport("user32.dll")]
        private static extern IntPtr DefWindowProc(IntPtr hWnd, int uMsg, IntPtr wParam, IntPtr lParam);

        [DllImport("user32.dll", SetLastError = true)]
        private static extern IntPtr RegisterPowerSettingNotification(IntPtr hRecipient, ref Guid PowerSettingGuid, int Flags);

        private const int WM_SYSCOMMAND = 0x0112;
        private const int SC_MONITORPOWER = 0xF170;
        private const int MONITOR_OFF = 2;

        private const int WM_POWERBROADCAST = 0x0218;
        private const int PBT_POWERSETTINGCHANGE = 0x8013;
        private const int DEVICE_NOTIFY_WINDOW_HANDLE = 0x00000000;

        // GUID_CONSOLE_DISPLAY_STATE: 6fe69556-704a-47a0-8f24-c28d936fda47
        // Data: 0 = Display Off, 1 = Display On, 2 = Display Dimmed
        private static Guid GUID_CONSOLE_DISPLAY_STATE = new Guid("6fe69556-704a-47a0-8f24-c28d936fda47");

        [StructLayout(LayoutKind.Sequential, Pack = 4)]
        private struct POWERBROADCAST_SETTING
        {
            public Guid PowerSetting;
            public uint DataLength;
            public byte Data;
        }

        private static PowerWatcherForm _hiddenForm;
        private static volatile int _displayState = 1; // 0 = Off, 1 = On, 2 = Dimmed
        private static volatile bool _isTurningOff = false;
        private static volatile int _lastBrightness = 10;
        private static long _reachedMinTick = 0;
        private static long _lastOffTick = 0;
        private static long _lastWakeTick = 0;

        private sealed class PowerWatcherForm : Form
        {
            private IntPtr _powerNotifyHandle = IntPtr.Zero;

            public PowerWatcherForm()
            {
                ShowInTaskbar = false;
                FormBorderStyle = FormBorderStyle.None;
                WindowState = FormWindowState.Minimized;
                Opacity = 0;
            }

            protected override void OnHandleCreated(EventArgs e)
            {
                base.OnHandleCreated(e);
                _powerNotifyHandle = RegisterPowerSettingNotification(
                    this.Handle,
                    ref GUID_CONSOLE_DISPLAY_STATE,
                    DEVICE_NOTIFY_WINDOW_HANDLE);
            }

            protected override void WndProc(ref Message m)
            {
                if (m.Msg == WM_POWERBROADCAST && m.WParam.ToInt32() == PBT_POWERSETTINGCHANGE && m.LParam != IntPtr.Zero)
                {
                    try
                    {
                        var setting = (POWERBROADCAST_SETTING)Marshal.PtrToStructure(m.LParam, typeof(POWERBROADCAST_SETTING));
                        if (setting.PowerSetting == GUID_CONSOLE_DISPLAY_STATE)
                        {
                            OnDisplayStateChanged(setting.Data);
                        }
                    }
                    catch { }
                }
                base.WndProc(ref m);
            }
        }

        private static void OnDisplayStateChanged(byte newState)
        {
            int prevState = _displayState;
            _displayState = newState;

            if (newState == 0 || newState == 2)
            {
                // Monitor is now OFF (0) or DIMMED (2).
                // Clear turning-off flag and never touch brightness while not in active ON (1) state.
                _isTurningOff = false;
            }
            else if (newState == 1 && prevState != 1)
            {
                // Monitor just woke up to active ON (1) state.
                _isTurningOff = false;
                _lastWakeTick = Environment.TickCount;

                ThreadPool.QueueUserWorkItem(_ =>
                {
                    Thread.Sleep(600);
                    if (_displayState == 1 && !_isTurningOff)
                    {
                        int current = GetCurrentBrightness();
                        if (current == 0)
                        {
                            _reachedMinTick = Environment.TickCount;
                            _lastBrightness = 1;
                            SetBrightness(1);
                        }
                        else
                        {
                            _lastBrightness = current;
                        }
                    }
                });
            }
        }

        [MTAThread]
        static void Main()
        {
            bool createdNew;
            using (var mutex = new Mutex(true, @"Local\AcerZeroBrightnessOffDaemon", out createdNew))
            {
                if (!createdNew)
                    return;

                using (var formReady = new ManualResetEvent(false))
                {
                    var uiThread = new Thread(() =>
                    {
                        _hiddenForm = new PowerWatcherForm();
                        IntPtr handle = _hiddenForm.Handle;
                        formReady.Set();
                        Application.Run();
                    });
                    uiThread.SetApartmentState(ApartmentState.STA);
                    uiThread.IsBackground = true;
                    uiThread.Start();
                    formReady.WaitOne(3000);
                }

                int initial = GetCurrentBrightness();
                if (initial == 0)
                {
                    SetBrightness(1);
                    _lastBrightness = 1;
                }
                else
                {
                    _lastBrightness = initial;
                }

                // Outer loop recreates WMI watcher automatically if GPU driver updates or WMI restarts
                while (true)
                {
                    try
                    {
                        var scope = new ManagementScope(@"\\.\root\WMI");
                        var query = new WqlEventQuery("SELECT * FROM WmiMonitorBrightnessEvent");

                        using (var watcher = new ManagementEventWatcher(scope, query))
                        {
                            watcher.Start();
                            while (true)
                            {
                                ManagementBaseObject ev = watcher.WaitForNextEvent();
                                int current = Convert.ToInt32(ev["Brightness"]);
                                long now = Environment.TickCount;

                                // Ignore all WMI brightness events while display is OFF (0), DIMMED (2),
                                // or currently in the middle of turning off.
                                if (_displayState != 1 || _isTurningOff)
                                    continue;

                                // Ignore brightness events immediately after display wake or turn-off
                                if (unchecked(now - _lastOffTick) < 2500 || unchecked(now - _lastWakeTick) < 900)
                                    continue;

                                if (current == 0)
                                {
                                    int prev = _lastBrightness;

                                    if (prev > 1)
                                    {
                                        // Step 1: User lowered brightness from >1% down to 0%.
                                        // Clamp to 1% so the screen stays dimly lit and the next F5 press triggers 1 -> 0.
                                        _reachedMinTick = now;
                                        _lastBrightness = 1;
                                        SetBrightness(1);
                                        continue;
                                    }

                                    // Step 2: Brightness was already at 1% (minimum) and user pressed F5 again.
                                    // Debounce auto-repeat so holding F5 from high brightness stops at 1% first.
                                    if (unchecked(now - _reachedMinTick) < 300)
                                    {
                                        _lastBrightness = 1;
                                        SetBrightness(1);
                                        continue;
                                    }

                                    // Turn off monitor WITHOUT calling SetBrightness(1) so we don't fight SC_MONITORPOWER!
                                    _isTurningOff = true;
                                    _lastOffTick = now;

                                    ThreadPool.QueueUserWorkItem(_ =>
                                    {
                                        Thread.Sleep(250);
                                        TurnOffMonitor();

                                        // Safety reset if user moved mouse during the 250ms delay and display stayed ON
                                        Thread.Sleep(3000);
                                        if (_isTurningOff)
                                        {
                                            _isTurningOff = false;
                                            if (_displayState == 1 && GetCurrentBrightness() == 0)
                                            {
                                                _lastBrightness = 1;
                                                SetBrightness(1);
                                            }
                                        }
                                    });
                                }
                                else
                                {
                                    _lastBrightness = current;
                                }
                            }
                        }
                    }
                    catch
                    {
                        Thread.Sleep(2000);
                    }
                }
            }
        }

        private static void TurnOffMonitor()
        {
            try
            {
                if (_hiddenForm != null && _hiddenForm.IsHandleCreated)
                {
                    _hiddenForm.BeginInvoke(new Action(() =>
                    {
                        DefWindowProc(_hiddenForm.Handle, WM_SYSCOMMAND, (IntPtr)SC_MONITORPOWER, (IntPtr)MONITOR_OFF);
                    }));
                }
            }
            catch { }
        }

        private static int GetCurrentBrightness()
        {
            try
            {
                using (var searcher = new ManagementObjectSearcher(@"\\.\root\WMI", "SELECT CurrentBrightness FROM WmiMonitorBrightness"))
                {
                    foreach (ManagementObject obj in searcher.Get())
                    {
                        return Convert.ToInt32(obj["CurrentBrightness"]);
                    }
                }
            }
            catch { }
            return 10;
        }

        private static void SetBrightness(byte target)
        {
            try
            {
                using (var searcher = new ManagementObjectSearcher(@"\\.\root\WMI", "SELECT * FROM WmiMonitorBrightnessMethods"))
                {
                    foreach (ManagementObject obj in searcher.Get())
                    {
                        using (ManagementBaseObject inParams = obj.GetMethodParameters("WmiSetBrightness"))
                        {
                            inParams["Timeout"] = (uint)0;
                            inParams["Brightness"] = target;
                            obj.InvokeMethod("WmiSetBrightness", inParams, null);
                        }
                    }
                }
            }
            catch { }
        }
    }
}
